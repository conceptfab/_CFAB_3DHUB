"""
Tile Manager - zarządzanie kafelkami w galerii.
"""

import logging
from typing import Optional

from src.models.file_pair import FilePair


class TileManager:
    """
    Zarządza kafelkami w galerii - tworzenie, aktualizacja, obsługa zdarzeń.
    """

    def __init__(
        self,
        main_window,
        gallery_manager=None,
        progress_manager=None,
        worker_manager=None,
        data_manager=None,
    ):
        """
        Inicjalizuje TileManager z wstrzykniętymi zależnościami.

        Args:
            main_window: Referencja do głównego okna
            gallery_manager: Opcjonalny gallery manager
            progress_manager: Opcjonalny progress manager
            worker_manager: Opcjonalny worker manager
            data_manager: Opcjonalny data manager
        """
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

        # Use injected managers or fallback to main_window
        self._gallery_manager = gallery_manager or getattr(
            main_window, "gallery_manager", None
        )
        self._progress_manager = progress_manager or getattr(
            main_window, "progress_manager", None
        )
        self._worker_manager = worker_manager or getattr(
            main_window, "worker_manager", None
        )
        self._data_manager = data_manager or getattr(main_window, "data_manager", None)

        # Thread-safe wskaźnik, czy trwa proces tworzenia kafelków
        import threading

        self._is_creating_tiles = False
        self._creation_lock = threading.RLock()

        # Batch processing optimization
        self._batch_size = 50
        self._memory_threshold_mb = 500

    def create_tile_widget_for_pair(self, file_pair: FilePair) -> Optional[object]:
        """
        Tworzy pojedynczy kafelek dla pary plików.
        """
        if not file_pair:
            self.logger.warning("Otrzymano None zamiast FilePair")
            return None

        if not hasattr(file_pair, "archive_path") or not file_pair.archive_path:
            self.logger.error(
                f"Nieprawidłowy FilePair - brak archive_path: {file_pair}"
            )
            return None

        gallery_manager = self._gallery_manager or self.main_window.gallery_manager
        tile = gallery_manager.create_tile_widget_for_pair(file_pair, self.main_window)
        if tile:
            # Podłącz sygnały kafelka
            tile.archive_open_requested.connect(self.main_window.open_archive)
            tile.preview_image_requested.connect(self.main_window._show_preview_dialog)
            tile.tile_selected.connect(self.main_window._handle_tile_selection_changed)
            tile.stars_changed.connect(self.main_window._handle_stars_changed)
            tile.color_tag_changed.connect(self.main_window._handle_color_tag_changed)
            tile.tile_context_menu_requested.connect(
                self.main_window._show_file_context_menu
            )

            # Podłącz callback do śledzenia ładowania miniaturek
            original_on_thumbnail_loaded = tile._on_thumbnail_loaded

            def thumbnail_loaded_callback(*args, **kwargs):
                try:
                    if (
                        hasattr(tile, "thumbnail_label")
                        and tile.thumbnail_label is not None
                    ):
                        try:
                            tile.thumbnail_label.isVisible()
                            result = original_on_thumbnail_loaded(*args, **kwargs)
                            progress_mgr = (
                                self._progress_manager
                                or self.main_window.progress_manager
                            )
                            progress_mgr.on_thumbnail_progress()
                            return result
                        except RuntimeError:
                            return None
                    else:
                        return None
                except Exception as e:
                    self.logger.warning(f"Błąd w thumbnail callback: {e}")
                    return None

            tile._on_thumbnail_loaded = thumbnail_loaded_callback

        return tile

    def start_tile_creation(self, file_pairs: list):
        """
        Thread-safe rozpoczęcie procesu tworzenia kafelków z memory monitoring.
        """
        with self._creation_lock:
            if self._is_creating_tiles:
                self.logger.warning(
                    "Próba rozpoczęcia tworzenia kafelków, gdy proces już trwa."
                )
                return

            self._is_creating_tiles = True

        # Monitor memory usage before batch processing
        import psutil

        try:
            memory_usage_mb = psutil.Process().memory_info().rss / 1024 / 1024
            if memory_usage_mb > self._memory_threshold_mb:
                self.logger.warning(f"High memory usage: {memory_usage_mb:.1f}MB")
                import gc

                gc.collect()
        except Exception:
            pass

        self.main_window.gallery_manager.tiles_container.setUpdatesEnabled(False)

        worker_mgr = self._worker_manager or self.main_window.worker_manager
        worker_mgr.start_data_processing_worker(file_pairs)

    def create_tile_widgets_batch(self, file_pairs_batch: list):
        """
        Tworzy kafelki dla batch'a par plików.
        Zamiast tworzyć po jednym kafelku, tworzy je grupami aby zmniejszyć obciążenie UI.

        Args:
            file_pairs_batch: Lista obiektów FilePair do przetworzenia w tym batch'u
        """
        batch_size = len(file_pairs_batch)

        # Memory pressure check before processing large batches
        if batch_size > 100:
            import psutil

            try:
                memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
                if memory_mb > self._memory_threshold_mb:
                    import gc

                    gc.collect()
            except Exception:
                pass

        # Resetuj liczniki na początku nowej operacji ładowania
        if not self.main_window.progress_manager.is_batch_processing():
            total_tiles = len(self.main_window.controller.current_file_pairs)
            self.main_window.progress_manager.init_batch_processing(total_tiles)

        try:
            created_count = 0

            # Oblicz geometrię layoutu żeby dodać kafelki w odpowiednich pozycjach
            gallery_manager = self.main_window.gallery_manager
            geometry = gallery_manager._get_cached_geometry()
            cols = geometry["cols"]

            # Pobierz aktualną liczbę kafelków w layoutu żeby kontynuować numerację
            current_tile_count = len(gallery_manager.gallery_tile_widgets)

            for idx, file_pair in enumerate(file_pairs_batch):
                tile = self.create_tile_widget_for_pair(file_pair)
                if tile:
                    # Dodaj kafelek do layoutu
                    total_position = current_tile_count + idx
                    row = total_position // cols
                    col = total_position % cols

                    # Dodaj do grid layout
                    gallery_manager.tiles_layout.addWidget(tile, row, col)

                    # Pokaż kafelek
                    tile.setVisible(True)

                    # Ustaw numer kafelka
                    tile_number = total_position + 1
                    total_tiles = len(self.main_window.controller.current_file_pairs)

                    tile.set_tile_number(tile_number, total_tiles)

                    # Wymuś aktualizację display
                    if hasattr(tile, "_update_filename_display"):
                        tile._update_filename_display()

                    created_count += 1

            # Update progress in batches for better performance
            progress_mgr = self._progress_manager or self.main_window.progress_manager
            gallery_mgr = self._gallery_manager or self.main_window.gallery_manager

            actual_tiles_count = len(gallery_mgr.gallery_tile_widgets)
            progress_mgr.update_tile_creation_progress(actual_tiles_count)

        finally:
            # Wymuś przetworzenie zdarzeń UI po każdym batchu
            from PyQt6.QtWidgets import QApplication

            QApplication.instance().processEvents()

    def refresh_existing_tiles(self, file_pairs_list: list):
        """
        Hash-based refresh istniejących kafli O(1) lookup.
        Nie tworzy nowych kafelków, tylko aktualizuje dane w istniejących.

        Args:
            file_pairs_list: Lista par plików z zaktualizowanymi metadanymi
        """
        if not file_pairs_list:
            return

        # Create hash map for O(1) lookup instead of O(n²)
        file_pairs_map = {
            fp.archive_path: fp
            for fp in file_pairs_list
            if hasattr(fp, "archive_path") and fp.archive_path
        }

        # Pobierz wszystkie istniejące kafelki z galerii
        existing_tiles = self.main_window.gallery_manager.get_all_tile_widgets()

        refreshed_count = 0
        for tile in existing_tiles:
            if hasattr(tile, "file_pair") and tile.file_pair:
                archive_path = tile.file_pair.archive_path
                if archive_path in file_pairs_map:
                    tile.update_data(file_pairs_map[archive_path])
                    refreshed_count += 1

        # Wymuś odświeżenie UI
        if hasattr(self.main_window.gallery_manager, "tiles_container"):
            self.main_window.gallery_manager.tiles_container.update()

    def on_tile_loading_finished(self):
        """
        Thread-safe zakończenie tworzenia wszystkich kafelków.
        """
        with self._creation_lock:
            self._is_creating_tiles = False

        # Włącz aktualizacje UI i wymuś odświeżenie
        self.main_window.gallery_manager.tiles_container.setUpdatesEnabled(True)
        self.main_window.gallery_manager.tiles_container.update()

        # Oznacz zakończenie tworzenia kafelków (50%)
        self.main_window.progress_manager.finish_tile_creation()

        # Delegacja do managera zamiast wywołania nieistniejącej metody
        if hasattr(self.main_window, "unpaired_files_tab_manager"):
            self.main_window.unpaired_files_tab_manager.update_unpaired_files_lists()

        # Przygotuj dane, w tym specjalne foldery
        if (
            hasattr(self.main_window.controller, "special_folders")
            and self.main_window.controller.special_folders
        ):
            self.main_window.gallery_manager.prepare_special_folders(
                self.main_window.controller.special_folders
            )

        # Zastosuj filtry i odśwież widok
        self.main_window.data_manager.apply_filters_and_update_view()

        # Pokaż interfejs
        self.main_window.filter_panel.setEnabled(True)
        is_gallery_populated = bool(self.main_window.gallery_manager.file_pairs_list)
        self.main_window.size_control_panel.setVisible(is_gallery_populated)

        # Jeśli galeria jest pusta po filtracji, zakończ proces
        if not is_gallery_populated:
            self.logger.warning(
                "Galeria pusta po zastosowaniu filtrów. Kończenie procesu ładowania."
            )
            self.main_window.progress_manager.show_progress(
                100, "Filtry nie zwróciły wyników."
            )
            from PyQt6.QtCore import QTimer

            QTimer.singleShot(500, self.main_window.progress_manager.hide_progress)
            return

        # Upewnij się że drzewo folderów jest widoczne
        if hasattr(self.main_window, "folder_tree"):
            self.main_window.folder_tree.setVisible(True)

        # Przywróć przycisk
        self.main_window.select_folder_button.setText("Wybierz Folder Roboczy")
        self.main_window.select_folder_button.setEnabled(True)

        # Pokaż przycisk odświeżania cache
        self.main_window.clear_cache_button.setVisible(True)

        # Zapisz metadane
        self.main_window._save_metadata()

        # Pokaż końcowy komunikat z rzeczywistą liczbą kafelków
        actual_tiles_count = len(self.main_window.gallery_manager.file_pairs_list)
        self.main_window.progress_manager.show_progress(
            100, f"✅ Załadowano {actual_tiles_count} kafelków!"
        )

        # Krótkie opóźnienie żeby użytkownik zobaczył 100% przed ukryciem
        from PyQt6.QtCore import QTimer

        QTimer.singleShot(500, self.main_window.progress_manager.hide_progress)

    def update_thumbnail_size(self):
        """
        Aktualizuje rozmiar miniatur na podstawie wartości suwaka.
        """
        # Deleguj do gallery_tab_manager
        self.main_window.gallery_tab_manager.update_thumbnail_size()

        # Deleguj również do unpaired_files_tab_manager dla skalowania
        if (
            hasattr(self.main_window, "unpaired_files_tab_manager")
            and self.main_window.unpaired_files_tab_manager
        ):
            # Pobierz aktualny rozmiar z gallery managera
            if (
                hasattr(self.main_window, "gallery_manager")
                and self.main_window.gallery_manager
            ):
                current_size = self.main_window.gallery_manager._current_size_tuple
                self.main_window.unpaired_files_tab_manager.update_thumbnail_size(
                    current_size
                )
