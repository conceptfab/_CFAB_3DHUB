"""
Manager galerii - zarządzanie wyświetlaniem kafelków.
"""

import logging
import math
import os
import threading
import time
import weakref
from typing import Any, Dict, List, Optional, Set, Tuple

from PyQt6.QtCore import QTimer, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QApplication,
    QGridLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src import app_config
from src.controllers.gallery_controller import GalleryController
from src.models.file_pair import FilePair
from src.models.special_folder import SpecialFolder
from src.ui.widgets.file_tile_widget import FileTileWidget
from src.ui.widgets.special_folder_tile_widget import SpecialFolderTileWidget
from src.ui.widgets.tile_resource_manager import get_resource_manager

logger = logging.getLogger(__name__)


class LayoutGeometry:
    """Thread-safe klasa pomocnicza do obliczeń geometrii layoutu."""

    def __init__(self, scroll_area, tiles_layout):
        self.scroll_area = scroll_area
        self.tiles_layout = tiles_layout

        # Thread-safe cache z timestamps
        self._cache: Dict[Tuple, Dict[str, Any]] = {}
        self._cache_lock = threading.RLock()
        self._cache_timestamps: Dict[Tuple, float] = {}
        self._cache_ttl = 5.0  # Cache TTL w sekundach

        # Cache statistics dla monitoring
        self._cache_stats = {"hits": 0, "misses": 0, "invalidations": 0}

    def get_layout_params(self, thumbnail_size: int) -> Dict[str, Any]:
        """Thread-safe zwracanie parametrów layoutu z intelligent caching."""
        current_time = time.time()

        cache_key = (
            self.scroll_area.width(),
            self.scroll_area.height(),
            thumbnail_size,
        )

        with self._cache_lock:
            # Check cache validity z TTL
            if (
                cache_key in self._cache
                and cache_key in self._cache_timestamps
                and current_time - self._cache_timestamps[cache_key] < self._cache_ttl
            ):

                self._cache_stats["hits"] += 1
                # Return copy dla thread safety
                return self._cache[cache_key].copy()

            # Cache miss or expired - calculate new params
            self._cache_stats["misses"] += 1

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
                "thumbnail_size": thumbnail_size,
                "calculated_at": current_time,
            }

            # Store w cache z timestamp
            self._cache[cache_key] = params
            self._cache_timestamps[cache_key] = current_time

            # Cleanup expired cache entries
            self._cleanup_expired_cache(current_time)

            return params.copy()

    def _cleanup_expired_cache(self, current_time: float):
        """Cleanup expired cache entries (called with lock held)."""
        expired_keys = [
            key
            for key, timestamp in self._cache_timestamps.items()
            if current_time - timestamp >= self._cache_ttl
        ]

        for key in expired_keys:
            self._cache.pop(key, None)
            self._cache_timestamps.pop(key, None)
            self._cache_stats["invalidations"] += 1

    def invalidate_cache(self):
        """Force invalidation całego cache (np. przy resize events)."""
        with self._cache_lock:
            cache_size = len(self._cache)
            self._cache.clear()
            self._cache_timestamps.clear()
            self._cache_stats["invalidations"] += cache_size

    def get_cache_stats(self) -> Dict[str, int]:
        """Zwróć cache statistics dla performance monitoring."""
        with self._cache_lock:
            stats = self._cache_stats.copy()
            stats["cache_size"] = len(self._cache)
            return stats

    def get_visible_range(
        self, thumbnail_size: int, total_items: int
    ) -> Tuple[int, int, Dict[str, Any]]:
        """Thread-safe obliczanie zakresu widocznych elementów z buffering."""
        params = self.get_layout_params(thumbnail_size)

        viewport_height = self.scroll_area.viewport().height()
        scroll_y = self.scroll_area.verticalScrollBar().value()

        # Intelligent buffering based on scroll speed
        base_buffer = viewport_height
        buffer = base_buffer

        visible_start_y = max(0, scroll_y - buffer)
        visible_end_y = scroll_y + viewport_height + buffer

        first_visible_row = max(
            0, math.floor(visible_start_y / params["tile_height_spacing"])
        )
        last_visible_row = math.ceil(visible_end_y / params["tile_height_spacing"])

        first_visible_item = first_visible_row * params["cols"]
        last_visible_item = min((last_visible_row + 1) * params["cols"], total_items)

        return first_visible_item, last_visible_item, params


class VirtualScrollingMemoryManager:
    """Memory management dla virtual scrolling kafli."""

    def __init__(self, gallery_manager):
        self.gallery_manager = gallery_manager

        # Widget tracking
        self.active_widgets: Dict[int, weakref.ref] = {}
        self.disposed_widgets: Set[int] = set()

        # Memory thresholds
        self.max_active_widgets = 200
        self.cleanup_threshold = 150

        # Statistics
        self.stats = {"widgets_created": 0, "widgets_disposed": 0, "memory_cleanups": 0}

    def register_widget(self, index: int, widget):
        """Register widget dla tracking."""
        if widget:
            self.active_widgets[index] = weakref.ref(
                widget, lambda ref: self._on_widget_destroyed(index)
            )
            self.stats["widgets_created"] += 1

            # Check memory pressure
            if len(self.active_widgets) > self.cleanup_threshold:
                self._trigger_memory_cleanup()

    def _on_widget_destroyed(self, index: int):
        """Callback gdy widget został zniszczony."""
        self.active_widgets.pop(index, None)
        self.disposed_widgets.add(index)

    def _trigger_memory_cleanup(self):
        """Trigger memory cleanup when threshold reached."""
        if not self.gallery_manager._virtualization_enabled:
            return

        # Get visible range
        if (
            hasattr(self.gallery_manager, "file_pairs_list")
            and self.gallery_manager.file_pairs_list
        ):
            total_items = len(self.gallery_manager.file_pairs_list)
            visible_start, visible_end, _ = (
                self.gallery_manager._geometry.get_visible_range(
                    self.gallery_manager._current_size_tuple[0], total_items
                )
            )

            # Dispose widgets outside visible range
            disposed_count = 0
            for index in list(self.active_widgets.keys()):
                if index < visible_start or index >= visible_end:
                    if self._dispose_widget_at_index(index):
                        disposed_count += 1

            self.stats["memory_cleanups"] += 1
            self.stats["widgets_disposed"] += disposed_count

    def _dispose_widget_at_index(self, index: int) -> bool:
        """Dispose widget at specific index."""
        widget_ref = self.active_widgets.get(index)
        if widget_ref:
            widget = widget_ref()
            if widget:
                # Remove z layout
                if hasattr(self.gallery_manager, "tiles_layout"):
                    self.gallery_manager.tiles_layout.removeWidget(widget)

                # Cleanup widget
                if hasattr(widget, "cleanup"):
                    widget.cleanup()
                elif hasattr(widget, "deleteLater"):
                    widget.deleteLater()

                # Remove z tracking
                self.active_widgets.pop(index, None)
                self.disposed_widgets.add(index)
                return True
        return False

    def get_memory_stats(self) -> Dict[str, int]:
        """Get memory management statistics."""
        stats = self.stats.copy()
        stats["active_widgets"] = len(self.active_widgets)
        stats["disposed_count"] = len(self.disposed_widgets)
        return stats


class GalleryManager:
    """
    Klasa zarządzająca galerią kafelków z thread safety.
    """

    VIRTUALIZATION_UPDATE_DELAY = 50  # ms, opóźnienie dla aktualizacji wirtualizacji

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
        self.scroll_area = scroll_area
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

        # Throttling scroll events
        self._scroll_timer = None
        self._last_scroll_update = 0
        self._scroll_throttle_ms = 16  # ~60 FPS for smooth scrolling
        self._scroll_debounce_ms = 100  # Debounce dla heavy operations

        # Progressive loading state
        self._progressive_loading = False
        self._loading_chunks_queue = []
        self._loading_lock = threading.RLock()

        if hasattr(self.scroll_area, "verticalScrollBar"):
            # Replace old scroll handler with throttled version
            self.scroll_area.verticalScrollBar().valueChanged.connect(
                self._on_scroll_throttled
            )
            self._setup_scroll_throttling()

        # Inicjalizacja flagi wirtualizacji
        self._virtualization_enabled = False  # ZAWSZE wyłączona

        # Memory management
        self.memory_manager = VirtualScrollingMemoryManager(self)

    def _setup_scroll_throttling(self):
        """Setup throttled scroll event handling."""
        if self.scroll_area and hasattr(self.scroll_area, "verticalScrollBar"):
            # Setup timer dla debounced operations
            self._scroll_timer = QTimer()
            self._scroll_timer.setSingleShot(True)
            self._scroll_timer.timeout.connect(self._on_scroll_debounced)

    def _on_scroll_throttled(self, value):
        """Throttled scroll handler - called at max ~60 FPS."""
        import time

        current_time = time.time() * 1000  # ms

        if current_time - self._last_scroll_update >= self._scroll_throttle_ms:
            self._last_scroll_update = current_time

            # Fast operations only - visibility updates
            self._update_visible_tiles_fast()

            # Schedule debounced heavy operations
            if self._scroll_timer:
                self._scroll_timer.stop()
                self._scroll_timer.start(self._scroll_debounce_ms)

    def _on_scroll_debounced(self):
        """Debounced scroll handler - heavy operations."""
        # Heavy operations po zakończeniu scroll
        self._update_geometry_cache_if_needed()
        self._cleanup_hidden_tiles()
        self._trigger_progressive_loading_if_needed()

    def _update_visible_tiles_fast(self):
        """Szybka aktualizacja widoczności kafli bez heavy operations."""
        # Wyłączono żeby kafle nie znikały
        return

    def _update_geometry_cache_if_needed(self):
        """Update geometry cache jeśli window size się zmienił."""
        if hasattr(self, "_geometry"):
            # Check czy trzeba invalidate cache
            current_size = (self.scroll_area.width(), self.scroll_area.height())
            if (
                not hasattr(self, "_last_window_size")
                or self._last_window_size != current_size
            ):
                self._geometry.invalidate_cache()
                self._last_window_size = current_size

    def _cleanup_hidden_tiles(self):
        """Cleanup tiles które są poza visible range (called by throttled scroll)."""
        if not self._virtualization_enabled:
            return

        # Delegate do memory manager
        if hasattr(self, "memory_manager"):
            self.memory_manager._trigger_memory_cleanup()

    def _trigger_progressive_loading_if_needed(self):
        """Trigger progressive loading jeśli są pending chunks."""
        with self._loading_lock:
            if self._loading_chunks_queue and not self._progressive_loading:
                self._start_progressive_loading()

    def _start_progressive_loading(self):
        """Start progressive loading - placeholder for now."""
        pass

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
            # NIE ukrywaj kafli na starcie
            tile.setVisible(True)  # ZAWSZE widoczne

            # Thread-safe dodanie do słownika
            with self._widgets_lock:
                self.gallery_tile_widgets[file_pair.get_archive_path()] = tile

            return tile
        except Exception as e:
            logger.error(f"Błąd tworzenia kafelka dla {file_pair.get_base_name()}: {e}")
            return None

    def update_gallery_view(self):
        """
        Aktualizuje widok galerii z wirtualizacją.
        """
        total_items = len(self.special_folders_list) + len(self.file_pairs_list)

        # Zmniejszono próg z 1500 na 200 - duże foldery używają DataProcessingWorker
        if total_items <= 200:
            self.force_create_all_tiles()
            # Wyłącz wirtualizację po force_create_all_tiles
            self._virtualization_enabled = False
            return

        # Dla folderów >200 kafelków używaj wirtualizacji - DataProcessingWorker już działa

        # Dla dużych folderów używaj wirtualizacji
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

            # NIE włączaj wirtualizacji
            self._virtualization_enabled = False  # ZAWSZE wyłączona

        finally:
            self.tiles_container.setUpdatesEnabled(True)

    def _update_visible_tiles(self):
        """Tworzy/usuwa kafelki w zależności od tego, czy są widoczne."""
        # CAŁKOWICIE WYŁĄCZONE - powodowało znikanie kafli
        return

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

            # Ustaw file_pairs_list PRZED wywołaniem update_gallery_view()
            self.file_pairs_list = filtered_pairs

            # Aktualizuj widok
            self.update_gallery_view()

        except Exception as e:
            logger.error(f"Błąd podczas aplikowania filtrów: {e}")
            # Fallback: pokaż wszystkie pliki
            self.file_pairs_list = all_file_pairs
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

            # Sprawdź, czy folder fizycznie istnieje, TYLKO jeśli nie jest wirtualny
            if not is_virtual and not os.path.exists(folder_path):
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

            return folder_widget
        except Exception as e:
            logger.error(f"Błąd tworzenia widgetu folderu: {e}", exc_info=True)
            return None

    def _on_folder_clicked(self, folder_path: str):
        """
        Obsługuje kliknięcie na kafelek folderu specjalnego.
        Otwiera folder w eksploratorze plików systemu.

        Args:
            folder_path (str): Ścieżka do folderu do otwarcia.
        """
        if not folder_path or not os.path.exists(folder_path):
            logger.warning(f"Próba otwarcia nieistniejącego folderu: {folder_path}")
            return

        try:
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))
        except Exception as e:
            logger.error(f"Nie udało się otworzyć folderu {folder_path}: {e}")

    def prepare_special_folders(self, special_folders: List[SpecialFolder]):
        """
        Przygotowuje widgety dla folderów specjalnych przed aktualizacją widoku.
        """
        self.special_folders_list = special_folders

        # Wyczyść poprzednie widgety folderów
        with self._widgets_lock:
            for folder_path in list(self.special_folder_widgets.keys()):
                folder_widget = self.special_folder_widgets.pop(folder_path)
                folder_widget.setParent(None)
                folder_widget.deleteLater()
            self.special_folder_widgets.clear()

        # Utwórz nowe widgety dla folderów
        for special_folder in special_folders:
            widget = self.create_folder_widget(special_folder)

    def set_special_folders(self, special_folders: List[SpecialFolder]):
        """
        Ustawia listę specjalnych folderów i OD RAZU odświeża widok.
        """
        # Krok 1: Przygotuj widgety w tle
        self.prepare_special_folders(special_folders)

        # Krok 2: Wymuś aktualizację widoku, aby pokazać nowe foldery
        self.update_gallery_view()

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

        # Wyłącz limit TileResourceManager dla force_create_all_tiles
        original_max_tiles = get_resource_manager().limits.max_tiles
        get_resource_manager().limits.max_tiles = 10000  # Tymczasowo zwiększ limit

        # Wyczyść stare kafelki przed tworzeniem nowych
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

            # Twórz kafelki w batchach - większe batche dla szybkości
            batch_size = 100  # Zwiększono z 20 na 100 dla szybkości SBSAR
            total_batches = (len(all_items) + batch_size - 1) // batch_size

            for batch_num in range(total_batches):
                start_idx = batch_num * batch_size
                end_idx = min(start_idx + batch_size, len(all_items))

                for i in range(start_idx, end_idx):
                    if i < len(self.special_folders_list):
                        # Twórz kafelki folderów specjalnych
                        folder = self.special_folders_list[i]
                        widget = SpecialFolderTileWidget(folder)
                        # Dodaj numerację kafelków
                        tooltip = f"[{i + 1}/{len(self.special_folders_list)}] {folder.folder_name}"
                        widget.setToolTip(tooltip)
                        widget.setObjectName(f"SpecialFolderTile_{i + 1}")
                        self.special_folder_widgets[folder.path] = widget
                        self.tiles_layout.addWidget(widget, i // cols, i % cols)
                    else:
                        # Twórz kafelki par plików
                        file_pair_idx = i - len(self.special_folders_list)
                        file_pair = self.file_pairs_list[file_pair_idx]
                        # Użyj prawdziwego FileTileWidget zamiast placeholder
                        widget = self.create_tile_widget_for_pair(
                            file_pair, self.tiles_container
                        )

                        if widget:
                            # Podłącz sygnały do kafelka (jak w tile_manager.py)
                            widget.archive_open_requested.connect(
                                self.main_window.open_archive
                            )
                            widget.preview_image_requested.connect(
                                self.main_window._show_preview_dialog
                            )
                            widget.tile_selected.connect(
                                self.main_window._handle_tile_selection_changed
                            )
                            widget.stars_changed.connect(
                                self.main_window._handle_stars_changed
                            )
                            widget.color_tag_changed.connect(
                                self.main_window._handle_color_tag_changed
                            )
                            widget.tile_context_menu_requested.connect(
                                self.main_window._show_file_context_menu
                            )

                            if hasattr(widget, "set_tile_number"):
                                widget.set_tile_number(i + 1, len(self.file_pairs_list))
                            widget.setObjectName(f"FileTile_{i + 1}")
                            self.gallery_tile_widgets[file_pair.archive_path] = widget
                            self.tiles_layout.addWidget(widget, i // cols, i % cols)
                        else:
                            logger.error(
                                f"Failed to create widget for {file_pair.get_base_name()}"
                            )
                            continue

                # Rzadsze processEvents - tylko co 5 batchów zamiast każdy
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

            # Wymuś pełny relayout i popraw polityki rozmiaru
            self.tiles_layout.invalidate()
            self.tiles_container.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum
            )
            self.tiles_container.adjustSize()
            self.tiles_container.updateGeometry()
            if hasattr(self.scroll_area, "widget"):
                self.scroll_area.widget().adjustSize()
            self.scroll_area.updateGeometry()

        except Exception as e:
            logger.error(f"Error in force_create_all_tiles: {e}")
            logger.error(traceback.format_exc())
        finally:
            self.tiles_container.setUpdatesEnabled(True)
            self.tiles_container.update()

            # Przywróć limit TileResourceManager
            get_resource_manager().limits.max_tiles = original_max_tiles

    def force_memory_cleanup(self):
        """Force memory cleanup - dla debug purposes."""
        if hasattr(self, "memory_manager"):
            self.memory_manager._trigger_memory_cleanup()

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics."""
        stats = {}

        if hasattr(self, "memory_manager"):
            stats["memory_manager"] = self.memory_manager.get_memory_stats()

        if hasattr(self, "_geometry"):
            stats["geometry_cache"] = self._geometry.get_cache_stats()

        # Add widget counts
        stats["total_widgets"] = len(getattr(self, "gallery_tile_widgets", []))
        stats["active_widgets"] = len(
            [w for w in getattr(self, "gallery_tile_widgets", []) if w]
        )

        return stats
