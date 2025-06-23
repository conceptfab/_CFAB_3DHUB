# PATCH-CODE DLA: TILE_MANAGER.PY

**Powiązany plik z analizą:** `../corrections/tile_manager_correction_kafli.md`
**Zasady ogólne:** `../../_BASE_/refactoring_rules.md`

---

### PATCH 1: PRZENIESIENIE IMPORTÓW I DODANIE ERROR HANDLING

**Problem:** Importy wewnątrz metod powodują overhead i problemy thread safety
**Rozwiązanie:** Przeniesienie importów na górę pliku i dodanie proper error handling

```python
"""
Tile Manager - zarządzanie kafelkami w galerii.
"""

import gc
import logging
import psutil
import threading
import time
from typing import Optional, Dict, Any

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication
from src.models.file_pair import FilePair


class MemoryMonitor:
    """Helper class dla thread-safe memory monitoring."""
    
    def __init__(self, threshold_mb: int = 500):
        self.threshold_mb = threshold_mb
        self._lock = threading.RLock()
    
    def check_and_cleanup_if_needed(self, logger) -> bool:
        """Sprawdza pamięć i wykonuje cleanup jeśli potrzeba. Returns True if cleanup was performed."""
        with self._lock:
            try:
                memory_usage_mb = psutil.Process().memory_info().rss / 1024 / 1024
                if memory_usage_mb > self.threshold_mb:
                    logger.warning(f"High memory usage: {memory_usage_mb:.1f}MB, performing cleanup")
                    gc.collect()
                    return True
                return False
            except (psutil.NoSuchProcess, psutil.AccessDenied, OSError) as e:
                logger.warning(f"Cannot monitor memory usage: {e}")
                return False


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
        batch_size: int = 50,
        memory_threshold_mb: int = 500,
    ):
        """
        Inicjalizuje TileManager z wstrzykniętymi zależnościami.

        Args:
            main_window: Referencja do głównego okna
            gallery_manager: Opcjonalny gallery manager
            progress_manager: Opcjonalny progress manager
            worker_manager: Opcjonalny worker manager
            data_manager: Opcjonalny data manager
            batch_size: Rozmiar batcha dla processing (domyślnie 50)
            memory_threshold_mb: Próg pamięci w MB (domyślnie 500)
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
        self._is_creating_tiles = False
        self._creation_lock = threading.RLock()

        # Configurable processing parameters
        self._batch_size = batch_size
        self._memory_monitor = MemoryMonitor(memory_threshold_mb)
```

---

### PATCH 2: REFAKTORYZACJA METODY START_TILE_CREATION

**Problem:** Redundant memory checks i brak timeout dla locków
**Rozwiązanie:** Użycie MemoryMonitor i dodanie timeout

```python
    def start_tile_creation(self, file_pairs: list):
        """
        Thread-safe rozpoczęcie procesu tworzenia kafelków z memory monitoring.
        """
        # Try to acquire lock with timeout to prevent deadlock
        if not self._creation_lock.acquire(timeout=5.0):
            self.logger.error("Failed to acquire creation lock within timeout")
            return

        try:
            if self._is_creating_tiles:
                self.logger.warning(
                    "Próba rozpoczęcia tworzenia kafelków, gdy proces już trwa."
                )
                return

            self._is_creating_tiles = True

            # Monitor memory usage before batch processing
            self._memory_monitor.check_and_cleanup_if_needed(self.logger)

            self.main_window.gallery_manager.tiles_container.setUpdatesEnabled(False)

            worker_mgr = self._worker_manager or self.main_window.worker_manager
            worker_mgr.start_data_processing_worker(file_pairs)

        finally:
            self._creation_lock.release()
```

---

### PATCH 3: OPTYMALIZACJA CREATE_TILE_WIDGETS_BATCH

**Problem:** Redundant memory checks i wielokrotne obliczenia geometrii
**Rozwiązanie:** Cache geometrii i optymalizacja memory checks

```python
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
            self._memory_monitor.check_and_cleanup_if_needed(self.logger)

        # Resetuj liczniki na początku nowej operacji ładowania
        if not self.main_window.progress_manager.is_batch_processing():
            total_tiles = len(self.main_window.controller.current_file_pairs)
            self.main_window.progress_manager.init_batch_processing(total_tiles)

        try:
            created_count = 0

            # Cache geometry calculation to avoid repeated computation
            gallery_manager = self.main_window.gallery_manager
            geometry = gallery_manager._get_cached_geometry()
            cols = geometry["cols"]

            # Pobierz aktualną liczbę kafelków w layoutu żeby kontynuować numerację
            current_tile_count = len(gallery_manager.gallery_tile_widgets)
            total_tiles = len(self.main_window.controller.current_file_pairs)

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
            QApplication.instance().processEvents()
```

---

### PATCH 4: OPTYMALIZACJA REFRESH_EXISTING_TILES

**Problem:** Redundant hasattr checks i brak optymalizacji
**Rozwiązanie:** Eliminacja niepotrzebnych sprawdzeń i optymalizacja

```python
    def refresh_existing_tiles(self, file_pairs_list: list):
        """
        Hash-based refresh istniejących kafli O(1) lookup.
        Nie tworzy nowych kafelków, tylko aktualizuje dane w istniejących.

        Args:
            file_pairs_list: Lista par plików z zaktualizowanymi metadanymi
        """
        if not file_pairs_list:
            return

        start_time = time.time()

        # Create hash map for O(1) lookup instead of O(n²)
        file_pairs_map = {}
        for fp in file_pairs_list:
            if fp and hasattr(fp, "archive_path") and fp.archive_path:
                file_pairs_map[fp.archive_path] = fp

        if not file_pairs_map:
            self.logger.warning("No valid file pairs to refresh")
            return

        # Pobierz wszystkie istniejące kafelki z galerii
        existing_tiles = self.main_window.gallery_manager.get_all_tile_widgets()

        refreshed_count = 0
        for tile in existing_tiles:
            # Optimize - check if tile has file_pair first
            if not (hasattr(tile, "file_pair") and tile.file_pair):
                continue
                
            archive_path = tile.file_pair.archive_path
            if archive_path in file_pairs_map:
                try:
                    tile.update_data(file_pairs_map[archive_path])
                    refreshed_count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to update tile for {archive_path}: {e}")

        # Wymuś odświeżenie UI
        if hasattr(self.main_window.gallery_manager, "tiles_container"):
            self.main_window.gallery_manager.tiles_container.update()

        elapsed_time = time.time() - start_time
        self.logger.info(f"Refreshed {refreshed_count} tiles in {elapsed_time:.2f}s")
```

---

### PATCH 5: REFAKTORYZACJA ON_TILE_LOADING_FINISHED

**Problem:** Zbyt duża metoda - należy podzielić na mniejsze metody
**Rozwiązanie:** Podział na logiczne metody pomocnicze

```python
    def on_tile_loading_finished(self):
        """
        Thread-safe zakończenie tworzenia wszystkich kafelków.
        """
        with self._creation_lock:
            self._is_creating_tiles = False

        try:
            self._finalize_ui_updates()
            self._handle_special_folders()
            self._apply_filters_and_show_results()
            self._finalize_progress_display()
        except Exception as e:
            self.logger.error(f"Error in tile loading finished: {e}")
            # Ensure UI is restored even if there's an error
            self._restore_ui_state()

    def _finalize_ui_updates(self):
        """Finalizuje aktualizacje UI po zakończeniu tworzenia kafli."""
        # Włącz aktualizacje UI i wymuś odświeżenie
        self.main_window.gallery_manager.tiles_container.setUpdatesEnabled(True)
        self.main_window.gallery_manager.tiles_container.update()

        # Oznacz zakończenie tworzenia kafelków (50%)
        self.main_window.progress_manager.finish_tile_creation()

        # Delegacja do managera zamiast wywołania nieistniejącej metody
        if hasattr(self.main_window, "unpaired_files_tab_manager"):
            self.main_window.unpaired_files_tab_manager.update_unpaired_files_lists()

    def _handle_special_folders(self):
        """Obsługuje przygotowanie specjalnych folderów."""
        # Przygotuj dane, w tym specjalne foldery
        if (
            hasattr(self.main_window.controller, "special_folders")
            and self.main_window.controller.special_folders
        ):
            self.main_window.gallery_manager.prepare_special_folders(
                self.main_window.controller.special_folders
            )

    def _apply_filters_and_show_results(self):
        """Stosuje filtry i wyświetla wyniki."""
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
            QTimer.singleShot(500, self.main_window.progress_manager.hide_progress)
            return

        # Upewnij się że drzewo folderów jest widoczne
        if hasattr(self.main_window, "folder_tree"):
            self.main_window.folder_tree.setVisible(True)

    def _finalize_progress_display(self):
        """Finalizuje wyświetlanie postępu."""
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
        QTimer.singleShot(500, self.main_window.progress_manager.hide_progress)

    def _restore_ui_state(self):
        """Przywraca stan UI w przypadku błędu."""
        try:
            self.main_window.gallery_manager.tiles_container.setUpdatesEnabled(True)
            self.main_window.filter_panel.setEnabled(True)
            self.main_window.select_folder_button.setEnabled(True)
        except Exception as e:
            self.logger.error(f"Failed to restore UI state: {e}")
```

---

### PATCH 6: OPTYMALIZACJA THUMBNAIL CALLBACK

**Problem:** Skomplikowany callback z try-except hell
**Rozwiązanie:** Uproszczenie logiki i lepsze error handling

```python
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
            self._connect_tile_signals(tile)
            self._setup_thumbnail_callback(tile)

        return tile

    def _connect_tile_signals(self, tile):
        """Łączy sygnały kafelka z handlerami."""
        signal_handlers = [
            (tile.archive_open_requested, self.main_window.open_archive),
            (tile.preview_image_requested, self.main_window._show_preview_dialog),
            (tile.tile_selected, self.main_window._handle_tile_selection_changed),
            (tile.stars_changed, self.main_window._handle_stars_changed),
            (tile.color_tag_changed, self.main_window._handle_color_tag_changed),
            (tile.tile_context_menu_requested, self.main_window._show_file_context_menu),
        ]
        
        for signal, handler in signal_handlers:
            try:
                signal.connect(handler)
            except Exception as e:
                self.logger.warning(f"Failed to connect signal {signal} to {handler}: {e}")

    def _setup_thumbnail_callback(self, tile):
        """Konfiguruje callback dla ładowania miniaturek."""
        if not hasattr(tile, "_on_thumbnail_loaded"):
            return

        original_callback = tile._on_thumbnail_loaded

        def enhanced_thumbnail_callback(*args, **kwargs):
            """Enhanced callback with proper error handling."""
            try:
                # Check if tile is still valid
                if not (hasattr(tile, "thumbnail_label") and tile.thumbnail_label):
                    return None

                # Check if widget is still accessible
                tile.thumbnail_label.isVisible()
                
                # Call original callback
                result = original_callback(*args, **kwargs)
                
                # Update progress
                progress_mgr = self._progress_manager or self.main_window.progress_manager
                progress_mgr.on_thumbnail_progress()
                
                return result
                
            except RuntimeError:
                # Widget was destroyed - this is normal during cleanup
                return None
            except Exception as e:
                self.logger.warning(f"Error in thumbnail callback: {e}")
                return None

        tile._on_thumbnail_loaded = enhanced_thumbnail_callback
```

---

## ✅ CHECKLISTA WERYFIKACYJNA (DO WYPEŁNIENIA PRZED WDROŻENIEM)

#### **FUNKCJONALNOŚCI DO WERYFIKACJI:**

- [ ] **Funkcjonalność podstawowa** - czy TileManager nadal tworzy kafle poprawnie.
- [ ] **API kompatybilność** - czy wszystkie publiczne metody działają jak wcześniej.
- [ ] **Obsługa błędów** - czy mechanizmy obsługi błędów nadal działają.
- [ ] **Walidacja danych** - czy walidacja FilePair działa poprawnie.
- [ ] **Logowanie** - czy system logowania działa bez spamowania.
- [ ] **Konfiguracja** - czy configurable batch_size i memory_threshold działają.
- [ ] **Cache** - czy cache geometrii działa poprawnie.
- [ ] **Thread safety** - czy kod jest bezpieczny w środowisku wielowątkowym.
- [ ] **Memory management** - czy MemoryMonitor działa i nie ma wycieków pamięci.
- [ ] **Performance** - czy wydajność batch processing nie została pogorszona.

#### **ZALEŻNOŚCI DO WERYFIKACJI:**

- [ ] **Importy** - czy wszystkie importy (threading, psutil, gc) działają poprawnie.
- [ ] **Zależności zewnętrzne** - czy psutil jest używane prawidłowo.
- [ ] **Zależności wewnętrzne** - czy powiązania z gallery_manager działają.
- [ ] **Cykl zależności** - czy nie wprowadzono cyklicznych zależności.
- [ ] **Backward compatibility** - czy kod jest kompatybilny wstecz.
- [ ] **Interface contracts** - czy interfejsy TileManager są przestrzegane.
- [ ] **Event handling** - czy obsługa sygnałów kafli działa poprawnie.
- [ ] **Signal/slot connections** - czy połączenia Qt działają.
- [ ] **Memory monitoring** - czy MemoryMonitor nie konfliktuje z innymi komponentami.

#### **TESTY WERYFIKACYJNE:**

- [ ] **Test jednostkowy** - czy wszystkie metody działają w izolacji.
- [ ] **Test integracyjny** - czy integracja z gallery_manager działa.
- [ ] **Test regresyjny** - czy nie wprowadzono regresji w tworzeniu kafli.
- [ ] **Test wydajnościowy** - czy batch processing 1000+ kafli jest wydajny.
- [ ] **Test thread safety** - czy operacje wielowątkowe są bezpieczne.
- [ ] **Test memory management** - czy memory monitoring działa poprawnie.

#### **KRYTERIA SUKCESU:**

- [ ] **WSZYSTKIE CHECKLISTY MUSZĄ BYĆ ZAZNACZONE** przed wdrożeniem.
- [ ] **BRAK FAILED TESTS** - wszystkie testy muszą przejść.
- [ ] **PERFORMANCE BUDGET** - wydajność nie pogorszona o więcej niż 5%.
- [ ] **CODE COVERAGE** - pokrycie kodu nie spadło poniżej 80%.
- [ ] **THREAD SAFETY VERIFIED** - brak deadlocków i race conditions.
- [ ] **MEMORY USAGE OPTIMIZED** - memory monitoring działa poprawnie.