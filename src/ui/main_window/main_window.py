"""
Główne okno aplikacji - zrefaktoryzowana wersja.
🚀 ETAP 2: Zoptymalizowane z Event Bus, ViewRefreshManager i OptimizedLogger
"""

from PyQt6.QtCore import QThreadPool, QTimer
from PyQt6.QtWidgets import QHBoxLayout, QMainWindow, QMessageBox, QVBoxLayout, QWidget

from src import app_config
from src.models.file_pair import FilePair
from src.services.thread_coordinator import ThreadCoordinator
from src.ui.delegates.workers import UnifiedBaseWorker
from src.ui.directory_tree.manager import DirectoryTreeManager
from src.ui.file_operations_ui import FileOperationsUI
from src.ui.gallery_manager import GalleryManager
from src.ui.main_window.main_window_interface import MainWindowInterface
from src.ui.main_window.window_initialization_manager import WindowInitializationManager


class MainWindow(QMainWindow):
    """
    Główne okno aplikacji CFAB_3DHUB - zrefaktoryzowana wersja.
    """

    def __init__(self, style_sheet=None):
        """
        Inicjalizuje główne okno aplikacji.
        ETAP 2.3: ManagerRegistry + Orchestrator
        """
        super().__init__()

        # ETAP 2.3: Inicjalizuj ManagerRegistry PRZED orchestrator
        from src.ui.main_window.manager_registry import ManagerRegistry

        self._manager_registry_new = ManagerRegistry(self)

        # ETAP 2: Centralna inicjalizacja przez Orchestrator
        from src.ui.main_window.main_window_orchestrator import MainWindowOrchestrator

        self._orchestrator = MainWindowOrchestrator(self)
        if not self._orchestrator.initialize_application():
            raise RuntimeError("Błąd inicjalizacji aplikacji przez Orchestrator")

        self.logger.info("Główne okno aplikacji zostało zainicjalizowane")

    # ETAP 2.3: Delegacja managerów do ManagerRegistry
    @property
    def interface(self):
        """Delegacja do ManagerRegistry."""
        return self._manager_registry_new.get_manager("interface")

    @property
    def window_initialization_manager(self):
        """Delegacja do ManagerRegistry."""
        return self._manager_registry_new.get_manager("window_initialization_manager")

    @property
    def ui_manager(self):
        """Delegacja do ManagerRegistry."""
        return self._manager_registry_new.get_manager("ui_manager")

    @property
    def tabs_manager(self):
        """Delegacja do ManagerRegistry."""
        return self._manager_registry_new.get_manager("tabs_manager")

    @property
    def gallery_manager(self):
        """Delegacja do ManagerRegistry."""
        return self._manager_registry_new.get_manager("gallery_manager")

    @property
    def metadata_manager(self):
        """Delegacja do ManagerRegistry."""
        return self._manager_registry_new.get_manager("metadata_manager")

    @property
    def progress_manager(self):
        """Delegacja do ManagerRegistry."""
        return self._manager_registry_new.get_manager("progress_manager")

    @property
    def thumbnail_size_manager(self):
        """Delegacja do ManagerRegistry."""
        return self._manager_registry_new.get_manager("thumbnail_size_manager")

    @property
    def tile_manager(self):
        """Delegacja do ManagerRegistry."""
        return self._manager_registry_new.get_manager("tile_manager")

    @property
    def scan_results_handler(self):
        """Delegacja do ManagerRegistry."""
        return self._manager_registry_new.get_manager("scan_results_handler")

    @property
    def scan_manager(self):
        """Delegacja do ManagerRegistry."""
        return self._manager_registry_new.get_manager("scan_manager")

    @property
    def worker_manager(self):
        """Delegacja do ManagerRegistry."""
        return self._manager_registry_new.get_manager("worker_manager")

    @property
    def data_manager(self):
        """Delegacja do ManagerRegistry."""
        return self._manager_registry_new.get_manager("data_manager")

    @property
    def selection_manager(self):
        """Delegacja do ManagerRegistry."""
        return self._manager_registry_new.get_manager("selection_manager")

    @property
    def bulk_operations_manager(self):
        """Delegacja do ManagerRegistry."""
        return self._manager_registry_new.get_manager("bulk_operations_manager")

    @property
    def bulk_move_operations_manager(self):
        """Delegacja do ManagerRegistry."""
        return self._manager_registry_new.get_manager("bulk_move_operations_manager")

    @property
    def file_operations_handler(self):
        """Delegacja do ManagerRegistry."""
        return self._manager_registry_new.get_manager("file_operations_handler")

    @property
    def dialog_manager(self):
        """Delegacja do ManagerRegistry."""
        return self._manager_registry_new.get_manager("dialog_manager")

    @property
    def controller_interface_manager(self):
        """Delegacja do ManagerRegistry."""
        return self._manager_registry_new.get_manager("controller_interface_manager")

    @property
    def event_handler(self):
        """Delegacja do ManagerRegistry."""
        return self._manager_registry_new.get_manager("event_handler")

    @property
    def file_operations_coordinator(self):
        """Delegacja do ManagerRegistry."""
        return self._manager_registry_new.get_manager("file_operations_coordinator")

    def show_preferences(self):
        """Wyświetla okno preferencji - direct implementation."""
        from src.ui.widgets.preferences_dialog import PreferencesDialog

        dialog = PreferencesDialog(self)
        dialog.exec()

    def remove_all_metadata_folders(self):
        """Usuwa wszystkie foldery metadanych - używa singleton."""
        # PRZED: DataManager(self) - tworzy nową instancję!
        # PO: używa singleton przez property
        self.data_manager.remove_all_metadata_folders()

    def start_metadata_cleanup_worker(self):
        """Uruchamia worker do czyszczenia metadanych - używa singleton."""
        # PRZED: DataManager(self) - tworzy nową instancję!
        # PO: używa singleton przez property
        self.data_manager.start_metadata_cleanup_worker()

    def show_about(self):
        """Wyświetla okno informacji o aplikacji - direct implementation."""
        from PyQt6.QtWidgets import QMessageBox

        about_text = (
            "CFAB_3DHUB - Menedżer plików 3D\n"
            "Wersja 2.0\n\n"
            "Aplikacja do zarządzania plikami 3D i ich podglądami."
        )
        QMessageBox.about(self, "O programie CFAB_3DHUB", about_text)

    def _connect_signals(self):
        """Podłącza sygnały do slotów - uproszczone."""
        # Podstawowe sygnały które nie wymagają lazy loaded managerów
        if hasattr(self, "folder_tree") and hasattr(self, "gallery_tab_manager"):
            self.folder_tree.clicked.connect(
                self.gallery_tab_manager.folder_tree_item_clicked
            )

    def closeEvent(self, event):
        """
        Obsługuje zamykanie aplikacji - ETAP 2.3: ManagerRegistry + Orchestrator.
        """
        try:
            # ETAP 2.3: Cleanup ManagerRegistry PRZED orchestrator
            if hasattr(self, "_manager_registry_new"):
                self._manager_registry_new.cleanup_managers()

            # ETAP 2: Centralne zarządzanie przez Orchestrator
            self._orchestrator.handle_shutdown()
            self.window_initialization_manager.handle_close_event(event)
        except Exception as e:
            self.logger.error(f"Błąd podczas zamykania aplikacji: {e}")
            event.accept()  # Zawsze akceptuj zamknięcie

    def _select_working_directory(self, directory_path=None):
        """Delegacja do Interface."""
        return self.interface.select_working_directory(directory_path)

    def _validate_directory_path(self, path: str) -> bool:
        """Delegacja do Interface."""
        return self.interface.validate_directory_path(path)

    def _stop_current_scanning(self):
        """Delegacja do Interface."""
        return self.interface.stop_current_scanning()

    def _start_folder_scanning(self, directory_path: str):
        """Delegacja do Interface."""
        return self.interface.start_folder_scanning(directory_path)

    def _on_scan_thread_finished(self):
        """Delegacja do Interface."""
        return self.interface.on_scan_thread_finished()

    def _force_refresh(self):
        """Delegacja do Interface."""
        return self.interface.force_refresh()

    def _clear_all_data_and_views(self):
        """Delegacja do Interface."""
        return self.interface.clear_all_data_and_views()

    def _clear_unpaired_files_lists(self):
        """Delegacja do Interface."""
        return self.interface.clear_unpaired_files_lists()

    def _update_unpaired_files_direct(self):
        """Delegacja do Interface."""
        return self.interface.update_unpaired_files_direct()

    def _handle_scan_finished(
        self, found_pairs, unpaired_archives, unpaired_previews, special_folders=None
    ):
        """Delegacja do Interface."""
        return self.interface.handle_scan_finished(
            found_pairs, unpaired_archives, unpaired_previews, special_folders
        )

    def _handle_scan_error(self, error_message: str):
        """Delegacja do Interface."""
        return self.interface.handle_scan_error(error_message)

    def _apply_filters_and_update_view(self):
        """Aplikuje filtry i odświeża widok - asynchroniczna implementacja."""

        def _async_apply_filters():
            """Asynchroniczna aplikacja filtrów."""
            try:
                if hasattr(self, "gallery_tab_manager"):
                    self.gallery_tab_manager.apply_filters_and_update_view()
                elif hasattr(self, "gallery_manager") and hasattr(self, "controller"):
                    # Fallback: wywołaj bezpośrednio gallery_manager z argumentami z kontrolera
                    all_file_pairs = getattr(self.controller, "current_file_pairs", [])
                    filter_criteria = (
                        {}
                    )  # Domyślne kryteria filtrowania (wszystkie pliki)
                    self.gallery_manager.apply_filters_and_update_view(
                        all_file_pairs, filter_criteria
                    )
            except Exception as e:
                self.logger.error(f"Błąd podczas aplikacji filtrów: {e}")

        # Wykonaj asynchronicznie żeby nie blokować UI
        QTimer.singleShot(0, _async_apply_filters)

    def _update_gallery_view(self):
        """Odświeża widok galerii - asynchroniczna implementacja."""

        def _async_update_gallery():
            """Asynchroniczne odświeżenie galerii."""
            try:
                if hasattr(self, "gallery_manager"):
                    self.gallery_manager.update_gallery_view()
            except Exception as e:
                self.logger.error(f"Błąd podczas odświeżania galerii: {e}")

        # Wykonaj asynchronicznie żeby nie blokować UI
        QTimer.singleShot(0, _async_update_gallery)

    def refresh_all_views(self, new_selection=None):
        """Odświeża wszystkie widoki - pozostaje delegacja do Interface."""
        return self.interface.refresh_all_views(new_selection)

    def force_full_refresh(self):
        """Wymusza pełne odświeżenie - pozostaje delegacja do Interface."""
        return self.interface.force_full_refresh()

    def _update_thumbnail_size(self):
        """Aktualizuje rozmiar miniaturek - direct implementation."""
        if hasattr(self, "thumbnail_size_manager"):
            self.thumbnail_size_manager.update_thumbnail_size()

    def resizeEvent(self, event):
        """Delegacja do Interface."""
        return self.interface.on_resize_timer_timeout()

    def _save_metadata(self):
        """Zapisuje metadane - direct implementation."""
        if hasattr(self, "metadata_manager") and self.metadata_manager:
            # Używa main_window/metadata_manager.py
            self.metadata_manager.save_metadata()

    def _schedule_metadata_save(self):
        """Planuje opóźnione zapisanie metadanych - direct implementation."""
        if hasattr(self, "metadata_manager") and self.metadata_manager:
            self.metadata_manager.schedule_metadata_save()

    def _force_immediate_metadata_save(self):
        """Wymusza natychmiastowe zapisanie metadanych - direct implementation."""
        if hasattr(self, "current_directory") and self.current_directory:
            from src.logic.metadata.metadata_core import MetadataManager

            metadata_manager = MetadataManager.get_instance(self.current_directory)
            metadata_manager.force_save()

    def _on_metadata_saved(self, success):
        """Obsługuje zakończenie zapisywania metadanych - direct implementation."""
        if success:
            self.logger.debug("Metadane zostały pomyślnie zapisane")
        else:
            self.logger.warning("Błąd podczas zapisywania metadanych")

    def open_archive(self, file_pair: FilePair):
        """Delegacja do Interface."""
        return self.interface.open_archive(file_pair)

    def _show_preview_dialog(self, file_pair: FilePair):
        """Delegacja do Interface."""
        return self.interface.show_preview_dialog(file_pair)

    def _handle_tile_selection_changed(self, file_pair: FilePair, is_selected: bool):
        """Delegacja do Interface."""
        return self.interface.handle_tile_selection_changed(file_pair, is_selected)

    def _update_bulk_operations_visibility(self):
        """Delegacja do Interface."""
        return self.interface.update_bulk_operations_visibility()

    def _clear_all_selections(self):
        """Czyści wszystkie selekcje - direct implementation."""
        if hasattr(self, "controller") and hasattr(
            self.controller, "selection_manager"
        ):
            self.controller.selection_manager.selected_tiles.clear()
        if hasattr(self, "gallery_manager"):
            self.gallery_manager.clear_all_selections()

    def _select_all_tiles(self):
        """Zaznacza wszystkie kafelki - direct implementation."""
        if hasattr(self, "gallery_manager"):
            self.gallery_manager.select_all_tiles()

    def _perform_bulk_delete(self):
        """Wykonuje masowe usuwanie - direct implementation."""
        if hasattr(self, "controller") and hasattr(
            self.controller, "selection_manager"
        ):
            selected_count = len(self.controller.selection_manager.selected_tiles)
            if selected_count > 0 and self.confirm_bulk_delete(selected_count):
                if hasattr(self, "file_operations_ui"):
                    self.file_operations_ui.perform_bulk_delete_operation()

    def _on_bulk_delete_finished(self, deleted_pairs):
        """
        Zoptymalizowana obsługa zakończenia masowego usuwania.
        Przeniesiona do background thread dla lepszej responsiveness.
        """
        if not deleted_pairs:
            self._show_progress(100, "Usuwanie przerwane")
            return

        # Zapamiętaj liczbę przed usunięciem
        original_count = len(self.controller.selection_manager.selected_tiles)

        # Background processing
        def update_data():
            """Update w tle."""
            for file_pair in deleted_pairs:
                if file_pair in self.controller.current_file_pairs:
                    self.controller.current_file_pairs.remove(file_pair)
                self.controller.selection_manager.selected_tiles.discard(file_pair)

        # Wykonaj update w tle
        QTimer.singleShot(0, update_data)

        # UI update
        self._apply_filters_and_update_view()
        self._schedule_metadata_save()

        # Pokaż wynik asynchronicznie
        QTimer.singleShot(
            100, lambda: self._show_delete_result(deleted_pairs, original_count)
        )

    def _show_delete_result(self, deleted_pairs, original_count):
        """Pokazuje wynik usuwania w tle."""
        self._show_progress(100, f"Usunięto {len(deleted_pairs)} par plików")

        # Non-blocking message
        QTimer.singleShot(
            0,
            lambda: QMessageBox.information(
                self,
                "Usuwanie zakończone",
                f"Usunięto {len(deleted_pairs)} z {original_count} par plików.",
            ),
        )

    def _perform_bulk_move(self):
        """Delegacja do Interface."""
        return self.interface.perform_bulk_move()

    def _on_bulk_move_finished(self, result):
        """Delegacja do Interface."""
        return self.interface.on_bulk_move_finished(result)

    def _refresh_source_folder_after_move(self):
        """Delegacja do Interface."""
        return self.interface.refresh_source_folder_after_move()

    def _handle_stars_changed(self, file_pair: FilePair, new_star_count: int):
        """Direct implementation - zmiana gwiazdek."""
        self.logger.info(
            f"🔥 _handle_stars_changed WYWOŁANY: {file_pair.get_base_name()} → {new_star_count} gwiazdek"
        )
        try:
            file_pair.set_stars(new_star_count)
            self.logger.info(f"✅ Gwiazdki ustawione w FilePair: {new_star_count}")
            self._schedule_metadata_save()
            self.logger.info(f"✅ Metadata save zaplanowany")

            # Opcjonalne: Natychmiastowa aktualizacja UI tile
            # self._update_tile_display(file_pair)

        except Exception as e:
            self.logger.error(f"❌ Błąd zmiany gwiazdek: {e}")
            import traceback

            self.logger.error(f"❌ Stack trace: {traceback.format_exc()}")

    def _handle_color_tag_changed(self, file_pair: FilePair, new_color_tag: str):
        """Direct implementation - zmiana tagu koloru."""
        try:
            file_pair.set_color_tag(new_color_tag)
            self._schedule_metadata_save()

            # Opcjonalne: Natychmiastowa aktualizacja UI tile
            # self._update_tile_display(file_pair)

        except Exception as e:
            self.logger.error(f"Błąd zmiany tagu koloru: {e}")

    def _show_file_context_menu(self, file_pair: FilePair, widget: QWidget, position):
        """Delegacja do Interface."""
        return self.interface.show_file_context_menu(file_pair, widget, position)

    def handle_file_drop_on_folder(
        self, source_file_paths: list[str], target_folder_path: str
    ):
        """Delegacja do Interface."""
        return self.interface.handle_file_drop_on_folder(
            source_file_paths, target_folder_path
        )

    # ---- Metody do obsługi operacji asynchronicznych i postępu ----

    def _show_progress(self, percent: int, message: str):
        """Wyświetla progress bar - direct implementation."""
        if hasattr(self, "progress_manager"):
            self.progress_manager.show_progress(percent, message)

    def _hide_progress(self):
        """Ukrywa progress bar - direct implementation."""
        if hasattr(self, "progress_manager"):
            self.progress_manager.hide_progress()

    def _setup_worker_connections(self, worker: UnifiedBaseWorker):
        """
        Konfiguruje połączenia sygnałów dla workera.

        Args:
            worker: Instancja UnifiedBaseWorker do skonfigurowania
        """
        worker.signals.progress.connect(self._show_progress)
        worker.signals.error.connect(self._handle_worker_error)

    def _handle_worker_error(self, error_message: str):
        """Delegacja do Interface."""
        return self.interface.handle_worker_error(error_message)

    def _show_detailed_move_report(
        self, moved_pairs, detailed_errors, skipped_files, summary
    ):
        """Delegacja do Interface."""
        return self.interface.show_detailed_move_report(
            moved_pairs, detailed_errors, skipped_files, summary
        )

    # ETAP 2 FINAL: Metody UI dla MainWindowController (MVC)
    def show_error_message(self, title: str, message: str):
        """Wyświetla komunikat błędu - asynchroniczna implementacja."""
        from PyQt6.QtWidgets import QMessageBox

        # Asynchroniczne wyświetlenie żeby nie blokować UI
        QTimer.singleShot(0, lambda: QMessageBox.critical(self, title, message))

    def show_warning_message(self, title: str, message: str):
        """Wyświetla ostrzeżenie - asynchroniczna implementacja."""
        from PyQt6.QtWidgets import QMessageBox

        # Asynchroniczne wyświetlenie żeby nie blokować UI
        QTimer.singleShot(0, lambda: QMessageBox.warning(self, title, message))

    def show_info_message(self, title: str, message: str):
        """Wyświetla informację - asynchroniczna implementacja."""
        from PyQt6.QtWidgets import QMessageBox

        # Asynchroniczne wyświetlenie żeby nie blokować UI
        QTimer.singleShot(0, lambda: QMessageBox.information(self, title, message))

    def update_scan_results(self, scan_result):
        """Delegacja do Interface."""
        return self.interface.update_scan_results(scan_result)

    def confirm_bulk_delete(self, count: int) -> bool:
        """Potwierdza masowe usuwanie - direct implementation."""
        from PyQt6.QtWidgets import QMessageBox

        # UWAGA: confirm_bulk_delete musi być synchroniczne bo zwraca bool
        # Ale można zoptymalizować przez ustawienie modality
        reply = QMessageBox.question(
            self,
            "Potwierdzenie usunięcia",
            f"Czy na pewno chcesz usunąć {count} par plików?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        return reply == QMessageBox.StandardButton.Yes

    def update_after_bulk_operation(self, processed_pairs, operation_name: str):
        """Aktualizuje widok po operacji masowej - asynchroniczna implementacja."""
        # UI update - synchroniczne
        self._apply_filters_and_update_view()
        self._schedule_metadata_save()

        # Message - asynchroniczne żeby nie blokować UI
        message = f"Zakończono {operation_name}: {len(processed_pairs)} par plików"
        QTimer.singleShot(
            100, lambda: self.show_info_message("Operacja zakończona", message)
        )

    def update_bulk_operations_visibility(self, selected_count: int):
        """Aktualizuje widoczność przycisków masowych - direct implementation."""
        if hasattr(self, "controller"):
            self.controller.update_bulk_operations_visibility(selected_count)

    def add_new_pair(self, new_pair):
        """Delegacja do Interface."""
        return self.interface.add_new_pair(new_pair)

    def update_unpaired_lists(self, archives, previews):
        """Delegacja do Interface."""
        return self.interface.update_unpaired_lists(archives, previews)

    def request_metadata_save(self):
        """Delegacja do Interface."""
        return self.interface.request_metadata_save()

    def change_directory(self, folder_path: str):
        """Delegacja do Interface."""
        return self.interface.change_directory(folder_path)

    def _finish_folder_change_without_tree_reset(self):
        """Delegacja do Interface."""
        return self.interface.finish_folder_change_without_tree_reset()

    # 🚨 ETAP 2 - POPRAWKA 5: Obsługa eksploratora plików
    def on_explorer_folder_changed(self, path: str):
        """Delegacja do Interface."""
        return self.interface.on_explorer_folder_changed(path)

    def on_explorer_file_selected(self, file_path: str):
        """Delegacja do Interface."""
        return self.interface.on_explorer_file_selected(file_path)

    def set_working_directory(self, directory: str):
        """Delegacja do Interface."""
        return self.interface.set_working_directory(directory)

    def _on_resize_timer_timeout(self):
        """Delegacja do Interface."""
        return self.interface.on_resize_timer_timeout()

    def _on_tile_data_processed(self, processed_pairs):
        """
        Callback po zakończeniu przetwarzania danych dla kafelków przez workera.
        Przekazuje sterowanie do TileManagera.
        """
        self.tile_manager.on_tile_loading_finished()

    def _on_tile_loading_finished(self):
        """
        Callback po zakończeniu tworzenia *wszystkich* widgetów kafelków.
        """
        self.tile_manager.on_tile_loading_finished()
