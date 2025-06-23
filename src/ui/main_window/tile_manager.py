"""
Tile Manager - zarządzanie kafelkami w galerii.
Przeniesione z MainWindow w ramach refaktoryzacji.
"""

import logging
from typing import Optional

from src.models.file_pair import FilePair


class TileManager:
    """
    Zarządza kafelkami w galerii - tworzenie, aktualizacja, obsługa zdarzeń.
    Przeniesione z MainWindow w ramach refaktoryzacji.
    """

    def __init__(self, main_window):
        """
        Inicjalizuje TileManager.

        Args:
            main_window: Referencja do głównego okna
        """
        self.main_window = main_window
        self.logger = logging.getLogger(__name__)

        # Wskaźnik, czy trwa proces tworzenia kafelków
        self._is_creating_tiles = False

    def create_tile_widget_for_pair(self, file_pair: FilePair) -> Optional[object]:
        """
        Tworzy pojedynczy kafelek dla pary plików.
        """
        # Walidacja danych wejściowych - Problem #4
        if not file_pair:
            logging.warning("Otrzymano None zamiast FilePair")
            return None

        if not hasattr(file_pair, "archive_path") or not file_pair.archive_path:
            logging.error(f"Nieprawidłowy FilePair - brak archive_path: {file_pair}")
            return None

        tile = self.main_window.gallery_manager.create_tile_widget_for_pair(
            file_pair, self.main_window
        )
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
                            self.main_window.progress_manager.on_thumbnail_progress()
                            return result
                        except RuntimeError:
                            logging.debug("Thumbnail callback: Widget usunięty")
                            return None
                    else:
                        logging.debug(
                            "Thumbnail callback: thumbnail_label nie istnieje"
                        )
                        return None
                except Exception as e:
                    logging.warning(f"Błąd w thumbnail callback: {e}")
                    return None

            tile._on_thumbnail_loaded = thumbnail_loaded_callback

        return tile

    def start_tile_creation(self, file_pairs: list):
        """
        Rozpoczyna proces tworzenia kafelków w partiach.
        """
        if self._is_creating_tiles:
            self.logger.warning("Próba rozpoczęcia tworzenia kafelków, gdy proces już trwa.")
            return
            
        self._is_creating_tiles = True
        self.main_window.gallery_manager.tiles_container.setUpdatesEnabled(False)
        self.logger.debug("Rozpoczęto tworzenie kafelków, aktualizacje UI wyłączone.")

        # Użyj workera do przetworzenia danych w tle
        self.main_window.worker_manager.start_data_processing_worker(file_pairs)

    def create_tile_widgets_batch(self, file_pairs_batch: list):
        """
        Tworzy kafelki dla batch'a par plików - OPTYMALIZACJA dla wydajności.
        Zamiast tworzyć po jednym kafelku, tworzy je grupami aby zmniejszyć obciążenie UI.

        Args:
            file_pairs_batch: Lista obiektów FilePair do przetworzenia w tym batch'u
        """
        # NAPRAWKA DEBUGGING: Sprawdź czy metoda w ogóle się wykonuje
        self.logger.info(f"🔧 DEBUG: create_tile_widgets_batch() CALLED with {len(file_pairs_batch)} file pairs")
        
        # Resetuj liczniki na początku nowej operacji ładowania
        if not self.main_window.progress_manager.is_batch_processing():
            total_tiles = len(self.main_window.controller.current_file_pairs)
            self.main_window.progress_manager.init_batch_processing(total_tiles)

        try:
            created_count = 0
            
            # NAPRAWKA KRYTYCZNA: Oblicz geometrię layoutu żeby dodać kafelki w odpowiednich pozycjach
            gallery_manager = self.main_window.gallery_manager
            geometry = gallery_manager._get_cached_geometry()
            cols = geometry["cols"]
            
            # NAPRAWKA KRYTYCZNA: Pobierz aktualną liczbę kafelków w layoutu żeby kontynuować numerację
            current_tile_count = len(gallery_manager.gallery_tile_widgets)
            
            for idx, file_pair in enumerate(file_pairs_batch):
                tile = self.create_tile_widget_for_pair(file_pair)
                if tile:
                    # NAPRAWKA KRYTYCZNA: DODAJ KAFELEK DO LAYOUTU!
                    total_position = current_tile_count + idx
                    row = total_position // cols
                    col = total_position % cols
                    
                    # Dodaj do grid layout
                    gallery_manager.tiles_layout.addWidget(tile, row, col)
                    
                    # Pokaż kafelek
                    tile.setVisible(True)
                    
                    # NAPRAWKA: Ustaw numer kafelka NA KOŃCU gdy już jest dodany do layoutu
                    tile_number = total_position + 1
                    total_tiles = len(self.main_window.controller.current_file_pairs)
                    
                    self.logger.debug(f"🔧 Setting tile number {tile_number}/{total_tiles} for tile at ({row}, {col})")
                    tile.set_tile_number(tile_number, total_tiles)
                    
                    # NAPRAWKA: Wymuś aktualizację display
                    if hasattr(tile, '_update_filename_display'):
                        tile._update_filename_display()
                    
                    created_count += 1
                    
                    self.logger.debug(f"🔧 Tile {tile_number} added to layout at ({row}, {col}) with number display")

            self.logger.info(f"🔧 DEBUG: Created {created_count} tiles from batch of {len(file_pairs_batch)} and ADDED TO LAYOUT")

            # NAPRAWKA PROGRESS BAR: Użyj rzeczywistego licznika kafelków z galerii
            actual_tiles_count = len(self.main_window.gallery_manager.gallery_tile_widgets)

            # NAPRAWKA PROGRESS BAR: Aktualizuj progress używając nowej metody
            self.main_window.progress_manager.update_tile_creation_progress(
                actual_tiles_count
            )

        finally:
            # NAPRAWKA WYDAJNOŚCI: Wymuś przetworzenie zdarzeń UI po każdym batchu,
            # aby aplikacja pozostała responsywna i progress bar się aktualizował.
            from PyQt6.QtWidgets import QApplication
            QApplication.instance().processEvents()

    def refresh_existing_tiles(self, file_pairs_list: list):
        """
        Odświeża istniejące kafelki po wczytaniu metadanych.
        Nie tworzy nowych kafelków, tylko aktualizuje dane w istniejących.

        Args:
            file_pairs_list: Lista par plików z zaktualizowanymi metadanymi
        """
        self.logger.debug(
            f"Odświeżanie {len(file_pairs_list)} istniejących kafelków po wczytaniu metadanych"
        )

        # Pobierz wszystkie istniejące kafelki z galerii
        existing_tiles = self.main_window.gallery_manager.get_all_tile_widgets()

        refreshed_count = 0
        for tile in existing_tiles:
            if hasattr(tile, "file_pair") and tile.file_pair:
                # Znajdź odpowiadającą parę plików w zaktualizowanej liście
                for updated_file_pair in file_pairs_list:
                    if (
                        hasattr(updated_file_pair, "archive_path")
                        and tile.file_pair.archive_path
                        == updated_file_pair.archive_path
                    ):
                        # Aktualizuj dane kafelka
                        tile.update_data(updated_file_pair)
                        refreshed_count += 1
                        break

        self.logger.debug(f"Odświeżono {refreshed_count} kafelków z metadanymi")

        # Wymuś odświeżenie UI
        if hasattr(self.main_window.gallery_manager, "tiles_container"):
            self.main_window.gallery_manager.tiles_container.update()

    def on_tile_loading_finished(self):
        """
        Wywoływane po zakończeniu tworzenia wszystkich kafelków.
        """
        self.logger.debug("Zakończono tworzenie wszystkich kafelków.")

        # Włącz aktualizacje UI i wymuś odświeżenie
        self.main_window.gallery_manager.tiles_container.setUpdatesEnabled(True)
        self.main_window.gallery_manager.tiles_container.update()
        self._is_creating_tiles = False
        self.logger.debug("Zakończono tworzenie kafelków, aktualizacje UI włączone i widok odświeżony.")

        # NAPRAWKA PROGRESS BAR: Oznacz zakończenie tworzenia kafelków (50%)
        self.main_window.progress_manager.finish_tile_creation()

        # Delegacja do managera zamiast wywołania nieistniejącej metody
        if hasattr(self.main_window, "unpaired_files_tab_manager"):
            self.main_window.unpaired_files_tab_manager.update_unpaired_files_lists()

        # NAJPIERW: Przygotuj dane, w tym specjalne foldery
        if (
            hasattr(self.main_window.controller, "special_folders")
            and self.main_window.controller.special_folders
        ):
            self.main_window.gallery_manager.prepare_special_folders(
                self.main_window.controller.special_folders
            )
            self.logger.info(
                f"Przygotowano {len(self.main_window.controller.special_folders)} specjalnych folderów do wyświetlenia"
            )

        # POTEM: Zastosuj filtry i odśwież widok RAZ, mając już wszystkie dane
        self.main_window.data_manager.apply_filters_and_update_view()

        # Pokaż interfejs
        self.main_window.filter_panel.setEnabled(True)
        is_gallery_populated = bool(self.main_window.gallery_manager.file_pairs_list)
        self.main_window.size_control_panel.setVisible(is_gallery_populated)

        # KRYTYCZNA NAPRAWKA: Jeśli galeria jest pusta po filtracji, nie można czekać
        # na ładowanie miniaturek, które nigdy się nie rozpocznie.
        if not is_gallery_populated:
            self.logger.warning("Galeria pusta po zastosowaniu filtrów. Kończenie procesu ładowania.")
            self.main_window.progress_manager.show_progress(100, "Filtry nie zwróciły wyników.")
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(500, self.main_window.progress_manager.hide_progress)
            # Zakończ metodę tutaj, aby nie pokazywać nieprawidłowych komunikatów o załadowaniu.
            return

        # Upewnij się że drzewo folderów jest widoczne
        if hasattr(self.main_window, "folder_tree"):
            self.main_window.folder_tree.setVisible(True)
            self.logger.debug(
                f"Drzewo folderów widoczne: "
                f"{self.main_window.folder_tree.isVisible()}"
            )
            self.logger.debug(f"Splitter rozmiary: {self.main_window.splitter.sizes()}")

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

        self.logger.debug(
            f"Widok zaktualizowany. Wyświetlono po filtracji: "
            f"{len(self.main_window.gallery_manager.file_pairs_list)}."
        )

    def update_thumbnail_size(self):
        """
        Aktualizuje rozmiar miniatur na podstawie wartości suwaka.
        """
        # Deleguj do gallery_tab_manager
        self.main_window.gallery_tab_manager.update_thumbnail_size()

        # NAPRAWKA: Deleguj również do unpaired_files_tab_manager dla skalowania
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
