"""
Tile Manager - zarządzanie kafelkami w galerii.
"""

import logging
import threading
import time
from typing import Optional

from src.models.file_pair import FilePair


class TileCreationMonitor:
    """Performance monitoring dla tile creation z adaptive optimization."""

    def __init__(self):
        self.metrics = {
            "tiles_created": 0,
            "total_time": 0,
            "memory_samples": [],
            "ui_blocking_events": 0,
            "gc_collections": 0,
            "batch_times": [],
        }
        self.adaptive_config = {
            "micro_batch_size": 5,
            "yield_interval": 25,
            "memory_check_interval": 50,
            "gc_trigger_threshold": 1000,  # MB
        }

    def start_monitoring(self, total_tiles: int):
        """Start monitoring session."""
        self.total_tiles = total_tiles
        self.start_time = time.time()
        self.metrics = {
            "tiles_created": 0,
            "total_time": 0,
            "memory_samples": [],
            "ui_blocking_events": 0,
            "gc_collections": 0,
            "batch_times": [],
        }

        # Adaptive configuration based on dataset size
        if total_tiles > 3000:
            self.adaptive_config["micro_batch_size"] = 3
            self.adaptive_config["yield_interval"] = 15
        elif total_tiles > 1500:
            self.adaptive_config["micro_batch_size"] = 5
            self.adaptive_config["yield_interval"] = 20
        else:
            self.adaptive_config["micro_batch_size"] = 10
            self.adaptive_config["yield_interval"] = 30

    def record_batch_completion(self, batch_size: int, batch_time: float):
        """Record batch completion metrics."""
        self.metrics["tiles_created"] += batch_size
        self.metrics["batch_times"].append(batch_time)

        # Adaptive micro-batch size based on performance
        avg_batch_time = sum(self.metrics["batch_times"][-5:]) / min(
            5, len(self.metrics["batch_times"])
        )

        if avg_batch_time > 0.1:  # >100ms per batch
            # Slow performance - reduce batch size
            self.adaptive_config["micro_batch_size"] = max(
                2, self.adaptive_config["micro_batch_size"] - 1
            )
        elif avg_batch_time < 0.02:  # <20ms per batch
            # Fast performance - can increase batch size
            self.adaptive_config["micro_batch_size"] = min(
                15, self.adaptive_config["micro_batch_size"] + 1
            )

    def check_memory_and_adapt(self) -> dict:
        """Check memory usage and adapt configuration."""
        try:
            import psutil

            memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
            self.metrics["memory_samples"].append(memory_mb)

            # Adaptive memory management
            if memory_mb > self.adaptive_config["gc_trigger_threshold"]:
                import gc

                gc.collect()
                self.metrics["gc_collections"] += 1

                # Reduce batch size if memory pressure
                self.adaptive_config["micro_batch_size"] = max(
                    2, self.adaptive_config["micro_batch_size"] - 1
                )
                self.adaptive_config["yield_interval"] = max(
                    10, self.adaptive_config["yield_interval"] - 5
                )

            return {
                "memory_mb": memory_mb,
                "warning": memory_mb > 1000,
                "critical": memory_mb > 1500,
                "adapted_config": self.adaptive_config.copy(),
            }
        except:
            return {"memory_mb": 0, "warning": False, "critical": False}

    def get_performance_summary(self) -> dict:
        """Get comprehensive performance summary."""
        total_time = time.time() - self.start_time if hasattr(self, "start_time") else 0

        return {
            "tiles_created": self.metrics["tiles_created"],
            "total_time": total_time,
            "tiles_per_second": (
                self.metrics["tiles_created"] / total_time if total_time > 0 else 0
            ),
            "average_memory": (
                sum(self.metrics["memory_samples"])
                / len(self.metrics["memory_samples"])
                if self.metrics["memory_samples"]
                else 0
            ),
            "peak_memory": (
                max(self.metrics["memory_samples"])
                if self.metrics["memory_samples"]
                else 0
            ),
            "ui_blocking_events": self.metrics["ui_blocking_events"],
            "gc_collections": self.metrics["gc_collections"],
            "final_config": self.adaptive_config.copy(),
        }


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
        self._is_creating_tiles = False
        self._creation_lock = threading.RLock()

        # Enhanced configuration for large datasets
        self._micro_batch_size = 5  # Micro-batches for UI responsiveness
        self._progress_update_interval = 10  # Update progress every 10 tiles
        self._memory_check_interval = 50  # Check memory every 50 tiles
        self._force_yield_interval = 25  # Force UI yield every 25 tiles

        # Cancel mechanism
        self._creation_cancelled = False
        self._creation_start_time = None

        # Performance tracking
        self._tiles_created_count = 0
        self._creation_metrics = {
            "tiles_per_second": 0,
            "memory_peak": 0,
            "ui_yields": 0,
        }

        # Performance monitor
        self.performance_monitor = TileCreationMonitor()

        # Batch processing optimization (legacy compatibility)
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

    def prepare_gallery_for_streaming(self, total_tiles: int):
        """Prepare gallery layout for streaming tile creation."""
        gallery_manager = self.main_window.gallery_manager

        # Pre-calculate final layout dimensions
        geometry = gallery_manager._get_cached_geometry()
        cols = geometry["cols"]

        # Calculate final container height
        import math

        rows = math.ceil(total_tiles / cols)
        tile_height = geometry["tile_height_spacing"]
        total_height = rows * tile_height

        # Set container size upfront to prevent layout thrashing
        gallery_manager.tiles_container.setMinimumHeight(total_height)

        # Prepare layout for efficient tile insertion
        gallery_manager.tiles_layout.setSpacing(geometry.get("spacing", 10))

        self.logger.debug(
            f"Gallery prepared for {total_tiles} tiles: {rows} rows x {cols} cols, "
            f"height: {total_height}px"
        )

    def coordinate_with_gallery_manager(self, file_pairs: list):
        """Enhanced coordination with gallery_manager."""
        gallery_manager = self.main_window.gallery_manager

        # Check if gallery_manager is trying to force_create_all_tiles
        if hasattr(gallery_manager, "_virtualization_enabled"):
            # Disable virtualization during streaming creation
            gallery_manager._virtualization_enabled = False
            self.logger.debug("Disabled gallery virtualization for streaming creation")

        # Prepare gallery layout
        self.prepare_gallery_for_streaming(len(file_pairs))

        # Override force_create_all_tiles to use streaming instead
        original_force_create = gallery_manager.force_create_all_tiles

        def streaming_force_create():
            self.logger.info("Redirecting force_create_all_tiles to streaming creation")
            # Use tile_manager streaming instead of monolithic creation
            return  # Let tile_manager handle it

        gallery_manager.force_create_all_tiles = streaming_force_create

        # Restore original method after completion
        def restore_force_create():
            gallery_manager.force_create_all_tiles = original_force_create

        # Schedule restoration
        from PyQt6.QtCore import QTimer

        QTimer.singleShot(0, restore_force_create)

    def start_tile_creation(self, file_pairs: list):
        """
        ENHANCED: Thread-safe tile creation start z cancel mechanism.
        """
        with self._creation_lock:
            if self._is_creating_tiles:
                self.logger.warning(
                    "Tile creation already in progress - attempting cancel"
                )
                self.cancel_tile_creation()

                # Wait briefly for cancellation
                time.sleep(0.5)

                if self._is_creating_tiles:
                    self.logger.error("Failed to cancel previous tile creation")
                    return

            self._is_creating_tiles = True
            self._creation_cancelled = False
            self._creation_start_time = time.time()

        # Reset metrics
        self._tiles_created_count = 0
        self._creation_metrics = {
            "tiles_per_second": 0,
            "memory_peak": 0,
            "ui_yields": 0,
        }

        # Start performance monitoring
        self.performance_monitor.start_monitoring(len(file_pairs))

        # Show cancel button in UI
        self._setup_cancel_ui()

        # Coordinate with gallery_manager before starting
        self.coordinate_with_gallery_manager(file_pairs)

        # Enhanced memory monitoring before starting
        memory_status = self._check_memory_before_batch(len(file_pairs))
        if memory_status.get("critical", False):
            self.logger.error(
                f"Cannot start tile creation - critical memory: {memory_status['memory_mb']:.0f}MB"
            )
            self._cleanup_tile_creation()

            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.warning(
                self.main_window,
                "Brak pamięci",
                f"Nie można rozpocząć tworzenia kafli - zbyt mało pamięci.\n"
                f"Aktualne zużycie: {memory_status['memory_mb']:.0f}MB\n\n"
                f"Zamknij inne aplikacje i spróbuj ponownie.",
            )
            return

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

        # Disable UI updates during initial setup
        self.main_window.gallery_manager.tiles_container.setUpdatesEnabled(False)

        # Start worker with enhanced monitoring
        worker_mgr = self._worker_manager or self.main_window.worker_manager
        worker_mgr.start_data_processing_worker(file_pairs)

    def cancel_tile_creation(self):
        """Cancel ongoing tile creation with graceful cleanup."""
        self.logger.warning("Cancelling tile creation")

        with self._creation_lock:
            self._creation_cancelled = True

            # Cancel any ongoing worker
            worker_mgr = self._worker_manager or self.main_window.worker_manager
            if hasattr(worker_mgr, "_emergency_cancel_operation"):
                worker_mgr._emergency_cancel_operation()

        # Cleanup UI state
        self._cleanup_tile_creation()

        # Show cancellation message
        self.main_window.progress_manager.show_progress(
            100, "Operacja anulowana przez użytkownika"
        )

        from PyQt6.QtCore import QTimer

        QTimer.singleShot(2000, self.main_window.progress_manager.hide_progress)

    def _setup_cancel_ui(self):
        """Setup cancel button in UI."""
        # Add cancel button to progress area
        if hasattr(self.main_window, "progress_bar") and hasattr(
            self.main_window, "progress_label"
        ):
            if not hasattr(self.main_window, "cancel_tile_button"):
                from PyQt6.QtWidgets import QPushButton

                self.main_window.cancel_tile_button = QPushButton("Anuluj")
                self.main_window.cancel_tile_button.setMaximumWidth(80)
                self.main_window.cancel_tile_button.clicked.connect(
                    self.cancel_tile_creation
                )

                # Add to layout next to progress bar (if possible)
                # This depends on the actual layout structure

            self.main_window.cancel_tile_button.setVisible(True)

    def _cleanup_tile_creation(self):
        """Cleanup tile creation state and UI."""
        with self._creation_lock:
            self._is_creating_tiles = False
            self._creation_cancelled = False

        # Re-enable UI updates
        if hasattr(self.main_window, "gallery_manager"):
            self.main_window.gallery_manager.tiles_container.setUpdatesEnabled(True)
            self.main_window.gallery_manager.tiles_container.update()

        # Hide cancel button
        if hasattr(self.main_window, "cancel_tile_button"):
            self.main_window.cancel_tile_button.setVisible(False)

        # Log final metrics
        if self._creation_start_time:
            total_duration = time.time() - self._creation_start_time
            self.logger.info(
                f"Tile creation session: {self._tiles_created_count} tiles, "
                f"{total_duration:.1f}s, {self._creation_metrics['tiles_per_second']:.1f} tiles/s, "
                f"peak memory: {self._creation_metrics['memory_peak']:.0f}MB, "
                f"UI yields: {self._creation_metrics['ui_yields']}"
            )

    def create_tile_widgets_batch(self, file_pairs_batch: list):
        """
        ENHANCED: Streaming tile creation with micro-batching and UI responsiveness.
        """
        batch_size = len(file_pairs_batch)

        # CRITICAL: Check for cancellation at start
        if self._creation_cancelled:
            self.logger.info("Tile creation cancelled - skipping batch")
            return

        self.logger.info(f"Creating {batch_size} tiles with streaming micro-batching")

        # Enhanced create_tile_widgets_batch with performance monitoring
        batch_start = time.time()

        # Get adaptive configuration from monitor
        config = self.performance_monitor.adaptive_config
        micro_batch = config["micro_batch_size"]
        yield_interval = config["yield_interval"]

        # Calculate adaptive micro-batch size based on total tiles
        total_tiles = len(self.main_window.controller.current_file_pairs)
        if total_tiles > 2000:
            micro_batch = 3  # Very small for huge datasets
        elif total_tiles > 1000:
            micro_batch = 5  # Small for large datasets
        else:
            micro_batch = 10  # Normal for regular datasets

        # Enhanced memory pressure check
        memory_status = self._check_memory_before_batch(batch_size)
        if memory_status.get("critical", False):
            self.logger.error(
                f"Critical memory pressure ({memory_status['memory_mb']:.0f}MB) - "
                f"reducing micro-batch to 2"
            )
            micro_batch = 2
            # Force aggressive garbage collection
            import gc

            gc.collect()

        # Track batch creation start
        batch_start_time = time.time()

        # Resetuj liczniki na początku nowej operacji ładowania
        if not self.main_window.progress_manager.is_batch_processing():
            total_tiles = len(self.main_window.controller.current_file_pairs)
            self.main_window.progress_manager.init_batch_processing(total_tiles)
            self._tiles_created_count = 0
            self._creation_start_time = batch_start_time

        try:
            # Get layout geometry once for the entire batch
            gallery_manager = self.main_window.gallery_manager
            geometry = gallery_manager._get_cached_geometry()
            cols = geometry["cols"]
            current_tile_count = len(gallery_manager.gallery_tile_widgets)

            # Disable UI updates for the batch to improve performance
            gallery_manager.tiles_container.setUpdatesEnabled(False)

            # Process batch in micro-batches for UI responsiveness
            for micro_start in range(0, len(file_pairs_batch), micro_batch):
                # Check for cancellation before each micro-batch
                if self._creation_cancelled:
                    self.logger.info(
                        f"Tile creation cancelled at {micro_start}/{batch_size}"
                    )
                    break

                micro_end = min(micro_start + micro_batch, len(file_pairs_batch))
                micro_batch_pairs = file_pairs_batch[micro_start:micro_end]

                # Create tiles in micro-batch
                for idx, file_pair in enumerate(micro_batch_pairs):
                    actual_idx = micro_start + idx

                    # Create single tile
                    tile = self.create_tile_widget_for_pair(file_pair)
                    if tile:
                        # Calculate position
                        total_position = current_tile_count + actual_idx
                        row = total_position // cols
                        col = total_position % cols

                        # Add to layout
                        gallery_manager.tiles_layout.addWidget(tile, row, col)
                        tile.setVisible(True)

                        # Set tile number
                        tile_number = total_position + 1
                        total_tiles = len(
                            self.main_window.controller.current_file_pairs
                        )
                        tile.set_tile_number(tile_number, total_tiles)

                        # Update display
                        if hasattr(tile, "_update_filename_display"):
                            tile._update_filename_display()

                        self._tiles_created_count += 1

                # Micro-yield: Allow UI to process events after each micro-batch
                from PyQt6.QtWidgets import QApplication

                QApplication.processEvents()
                self._creation_metrics["ui_yields"] += 1

                # Update progress more frequently for better UX
                if (micro_start + micro_batch) % self._progress_update_interval == 0:
                    progress_mgr = (
                        self._progress_manager or self.main_window.progress_manager
                    )
                    actual_tiles_count = len(gallery_manager.gallery_tile_widgets)
                    progress_mgr.update_tile_creation_progress(actual_tiles_count)

                # Memory check every N tiles
                if (micro_start + micro_batch) % self._memory_check_interval == 0:
                    memory_status = self._check_memory_during_creation()
                    if memory_status.get("warning", False):
                        # Trigger garbage collection
                        import gc

                        gc.collect()

                    if memory_status.get("critical", False):
                        self.logger.error(
                            "Critical memory during tile creation - stopping"
                        )
                        self._creation_cancelled = True
                        break

                # Brief pause for very large datasets to prevent system overload
                if total_tiles > 2000:
                    time.sleep(0.002)  # 2ms pause for huge datasets

            # Final progress update for this batch
            progress_mgr = self._progress_manager or self.main_window.progress_manager
            actual_tiles_count = len(gallery_manager.gallery_tile_widgets)
            progress_mgr.update_tile_creation_progress(actual_tiles_count)

        finally:
            # Always re-enable UI updates
            gallery_manager.tiles_container.setUpdatesEnabled(True)

            # Force one final UI update
            from PyQt6.QtWidgets import QApplication

            QApplication.processEvents()

            # Log batch performance
            batch_duration = time.time() - batch_start_time
            tiles_per_second = batch_size / batch_duration if batch_duration > 0 else 0
            self._creation_metrics["tiles_per_second"] = tiles_per_second

            # Record batch completion
            batch_time = time.time() - batch_start
            self.performance_monitor.record_batch_completion(
                len(file_pairs_batch), batch_time
            )

            # Log adaptive performance info
            if len(file_pairs_batch) % 200 == 0:  # Every 200 tiles
                summary = self.performance_monitor.get_performance_summary()
                self.logger.info(
                    f"Tile creation performance: {summary['tiles_per_second']:.1f} tiles/s, "
                    f"memory: {summary['average_memory']:.0f}MB avg, "
                    f"adaptive batch: {micro_batch}"
                )

            self.logger.info(
                f"Batch completed: {batch_size} tiles in {batch_duration:.2f}s "
                f"({tiles_per_second:.1f} tiles/s)"
            )

    def _check_memory_before_batch(self, batch_size: int) -> dict:
        """Check memory status before creating a batch of tiles."""
        try:
            import psutil

            memory_mb = psutil.Process().memory_info().rss / 1024 / 1024

            # Adaptive thresholds based on batch size
            base_warning = 800  # 800MB base warning
            base_critical = 1200  # 1.2GB base critical

            # Increase thresholds for larger batches
            warning_threshold = base_warning + (batch_size * 2)  # +2MB per tile
            critical_threshold = base_critical + (batch_size * 3)  # +3MB per tile

            return {
                "memory_mb": memory_mb,
                "warning": memory_mb > warning_threshold,
                "critical": memory_mb > critical_threshold,
                "batch_size": batch_size,
            }
        except Exception as e:
            self.logger.warning(f"Memory check failed: {e}")
            return {"memory_mb": 0, "warning": False, "critical": False}

    def _check_memory_during_creation(self) -> dict:
        """Lightweight memory check during tile creation."""
        try:
            import psutil

            memory_mb = psutil.Process().memory_info().rss / 1024 / 1024

            # Store peak memory for metrics
            if memory_mb > self._creation_metrics["memory_peak"]:
                self._creation_metrics["memory_peak"] = memory_mb

            return {
                "memory_mb": memory_mb,
                "warning": memory_mb > 1000,  # 1GB warning
                "critical": memory_mb > 1500,  # 1.5GB critical
            }
        except:
            return {"memory_mb": 0, "warning": False, "critical": False}

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
        ENHANCED: Thread-safe completion z comprehensive cleanup.
        """
        # Get final performance summary
        summary = self.performance_monitor.get_performance_summary()

        self.logger.info(
            f"Tile creation completed: {summary['tiles_created']} tiles in "
            f"{summary['total_time']:.1f}s ({summary['tiles_per_second']:.1f} tiles/s), "
            f"peak memory: {summary['peak_memory']:.0f}MB, "
            f"GC runs: {summary['gc_collections']}"
        )

        # Cleanup tile creation state
        self._cleanup_tile_creation()

        # Enhanced completion handling
        try:
            # Enable UI updates and force refresh
            self.main_window.gallery_manager.tiles_container.setUpdatesEnabled(True)
            self.main_window.gallery_manager.tiles_container.update()

            # Mark tile creation complete (50% progress)
            self.main_window.progress_manager.finish_tile_creation()

            # Continue with existing completion logic
            if hasattr(self.main_window, "unpaired_files_tab_manager"):
                self.main_window.unpaired_files_tab_manager.update_unpaired_files_lists()

            # Prepare special folders
            if (
                hasattr(self.main_window.controller, "special_folders")
                and self.main_window.controller.special_folders
            ):
                self.main_window.gallery_manager.prepare_special_folders(
                    self.main_window.controller.special_folders
                )

            # Apply filters and refresh view
            self.main_window.data_manager.apply_filters_and_update_view()

            # Show interface
            self.main_window.filter_panel.setEnabled(True)
            is_gallery_populated = bool(
                self.main_window.gallery_manager.file_pairs_list
            )
            self.main_window.size_control_panel.setVisible(is_gallery_populated)

            # Handle empty gallery after filtering
            if not is_gallery_populated:
                self.logger.warning("Gallery empty after filters - completing process")
                self.main_window.progress_manager.show_progress(
                    100, "Filtry nie zwróciły wyników."
                )
                from PyQt6.QtCore import QTimer

                QTimer.singleShot(500, self.main_window.progress_manager.hide_progress)
                return

            # Show folder tree
            if hasattr(self.main_window, "folder_tree"):
                self.main_window.folder_tree.setVisible(True)

            # Restore UI elements
            self.main_window.select_folder_button.setText("Wybierz Folder Roboczy")
            self.main_window.select_folder_button.setEnabled(True)
            self.main_window.clear_cache_button.setVisible(True)

            # Save metadata
            self.main_window._save_metadata()

            # Show completion message
            actual_tiles_count = len(self.main_window.gallery_manager.file_pairs_list)
            self.main_window.progress_manager.show_progress(
                100, f"✅ Załadowano {actual_tiles_count} kafelków!"
            )

            # Hide progress after delay
            from PyQt6.QtCore import QTimer

            QTimer.singleShot(500, self.main_window.progress_manager.hide_progress)

        except Exception as e:
            self.logger.error(f"Error in tile loading completion: {e}")
            self._cleanup_tile_creation()

            # Show error to user
            from PyQt6.QtWidgets import QMessageBox

            QMessageBox.warning(
                self.main_window,
                "Błąd zakończenia",
                f"Wystąpił błąd podczas finalizacji tworzenia kafli:\n{str(e)}\n\n"
                f"Aplikacja może działać nieprawidłowo.",
            )

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
