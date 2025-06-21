"""
MainWindow Interface - grupuje delegacje metod według odpowiedzialności.
Wydzielone z MainWindow dla lepszej organizacji kodu.
"""

from src.models.file_pair import FilePair


class MainWindowInterface:
    """
    Interface grouping delegation methods by responsibility.
    Organizuje delegacje w logiczne grupy zamiast rozrzuconych po całym MainWindow.
    """

    def __init__(self, main_window):
        """
        Inicjalizuje interface.

        Args:
            main_window: Referencja do głównego okna aplikacji
        """
        self.main_window = main_window

    # === UI OPERATIONS ===
    def show_preferences(self):
        """Delegacja: Pokaż preferencje."""
        return self.main_window.ui_manager.show_preferences()

    def show_about(self):
        """Delegacja: Pokaż informacje o aplikacji."""
        return self.main_window.ui_manager.show_about()

    def remove_all_metadata_folders(self):
        """Delegacja: Usuń wszystkie foldery metadanych."""
        return self.main_window.ui_manager.remove_all_metadata_folders()

    def start_metadata_cleanup_worker(self):
        """Delegacja: Uruchom worker czyszczenia metadanych."""
        return self.main_window.ui_manager.start_metadata_cleanup_worker()

    # === SCAN OPERATIONS ===
    def select_working_directory(self, directory_path=None):
        """Delegacja: Wybierz katalog roboczy."""
        return self.main_window.scan_manager.select_working_directory(directory_path)

    def validate_directory_path(self, path: str) -> bool:
        """Delegacja: Waliduj ścieżkę katalogu."""
        return self.main_window.scan_manager.validate_directory_path(path)

    def stop_current_scanning(self):
        """Delegacja: Zatrzymaj bieżące skanowanie."""
        return self.main_window.scan_manager.stop_current_scanning()

    def start_folder_scanning(self, directory_path: str):
        """Delegacja: Rozpocznij skanowanie folderu."""
        return self.main_window.scan_manager.start_folder_scanning(directory_path)

    def on_scan_thread_finished(self):
        """Delegacja: Obsłuż zakończenie wątku skanowania."""
        return self.main_window.scan_manager.on_scan_thread_finished()

    # === DATA OPERATIONS ===
    def force_refresh(self):
        """Delegacja: Wymuś odświeżenie."""
        return self.main_window.data_manager.force_refresh()

    def clear_all_data_and_views(self):
        """Delegacja: Wyczyść wszystkie dane i widoki."""
        return self.main_window.data_manager.clear_all_data_and_views()

    def clear_unpaired_files_lists(self):
        """Delegacja: Wyczyść listy niesparowanych plików."""
        return self.main_window.data_manager.clear_unpaired_files_lists()

    def update_unpaired_files_direct(self):
        """Delegacja: Zaktualizuj niesparowane pliki bezpośrednio."""
        return self.main_window.data_manager.update_unpaired_files_direct()

    def apply_filters_and_update_view(self):
        """Delegacja: Zastosuj filtry i zaktualizuj widok."""
        return self.main_window.data_manager.apply_filters_and_update_view()

    def update_gallery_view(self):
        """Delegacja: Zaktualizuj widok galerii."""
        return self.main_window.data_manager.update_gallery_view()

    def refresh_all_views(self, new_selection=None):
        """Delegacja: Odśwież wszystkie widoki."""
        return self.main_window.data_manager.refresh_all_views(new_selection)

    def force_full_refresh(self):
        """Delegacja: Wymuś pełne odświeżenie."""
        return self.main_window.data_manager.force_full_refresh()

    # === SCAN RESULTS OPERATIONS ===
    def handle_scan_finished(
        self, found_pairs, unpaired_archives, unpaired_previews, special_folders=None
    ):
        """Delegacja: Obsłuż zakończenie skanowania."""
        return self.main_window.scan_results_handler.handle_scan_finished(
            found_pairs, unpaired_archives, unpaired_previews, special_folders
        )

    def handle_scan_error(self, error_message: str):
        """Delegacja: Obsłuż błąd skanowania."""
        return self.main_window.scan_results_handler.handle_scan_error(error_message)

    def change_directory(self, folder_path: str):
        """Delegacja: Zmień katalog."""
        return self.main_window.scan_results_handler.change_directory(folder_path)

    def finish_folder_change_without_tree_reset(self):
        """Delegacja: Zakończ zmianę folderu bez resetu drzewa."""
        return (
            self.main_window.scan_results_handler.finish_folder_change_without_tree_reset()
        )

    # === METADATA OPERATIONS ===
    def save_metadata(self):
        """Delegacja: Zapisz metadane."""
        return self.main_window.metadata_manager.save_metadata()

    def schedule_metadata_save(self):
        """Delegacja: Zaplanuj zapis metadanych."""
        return self.main_window.metadata_manager.schedule_metadata_save()

    def force_immediate_metadata_save(self):
        """Delegacja: Wymuś natychmiastowy zapis metadanych."""
        return self.main_window.metadata_manager.force_immediate_metadata_save()

    def on_metadata_saved(self, success):
        """Delegacja: Obsłuż zapisane metadane."""
        return self.main_window.metadata_manager.on_metadata_saved(success)

    def handle_stars_changed(self, file_pair: FilePair, new_star_count: int):
        """Delegacja: Obsłuż zmianę gwiazdek."""
        return self.main_window.metadata_manager.handle_stars_changed(
            file_pair, new_star_count
        )

    def handle_color_tag_changed(self, file_pair: FilePair, new_color_tag: str):
        """Delegacja: Obsłuż zmianę tagu kolorów."""
        return self.main_window.metadata_manager.handle_color_tag_changed(
            file_pair, new_color_tag
        )

    # === SELECTION OPERATIONS ===
    def handle_tile_selection_changed(self, file_pair: FilePair, is_selected: bool):
        """Delegacja: Obsłuż zmianę selekcji kafelka."""
        return self.main_window.selection_manager.handle_tile_selection_changed(
            file_pair, is_selected
        )

    def update_bulk_operations_visibility(self):
        """Delegacja: Zaktualizuj widoczność operacji masowych."""
        return self.main_window.selection_manager.update_bulk_operations_visibility()

    def clear_all_selections(self):
        """Delegacja: Wyczyść wszystkie selekcje."""
        return self.main_window.selection_manager.clear_all_selections()

    def select_all_tiles(self):
        """Delegacja: Zaznacz wszystkie kafelki."""
        return self.main_window.selection_manager.select_all_tiles()

    # === BULK OPERATIONS ===
    def perform_bulk_delete(self):
        """Delegacja: Wykonaj masowe usuwanie."""
        return self.main_window.bulk_operations_manager.perform_bulk_delete()

    def perform_bulk_move(self):
        """Delegacja: Wykonaj masowe przenoszenie."""
        return self.main_window.bulk_move_operations_manager.perform_bulk_move()

    def on_bulk_move_finished(self, result):
        """Delegacja: Obsłuż zakończenie masowego przenoszenia."""
        return self.main_window.bulk_move_operations_manager.on_bulk_move_finished(
            result
        )

    def refresh_source_folder_after_move(self):
        """Delegacja: Odśwież folder źródłowy po przeniesieniu."""
        return (
            self.main_window.bulk_move_operations_manager.refresh_source_folder_after_move()
        )

    # === FILE OPERATIONS ===
    def open_archive(self, file_pair: FilePair):
        """Delegacja: Otwórz archiwum."""
        return self.main_window.file_operations_handler.open_archive(file_pair)

    def show_file_context_menu(self, file_pair: FilePair, widget, position):
        """Delegacja: Pokaż menu kontekstowe pliku."""
        return self.main_window.file_operations_handler.show_file_context_menu(
            file_pair, widget, position
        )

    def handle_file_drop_on_folder(self, source_file_paths, target_folder_path: str):
        """Delegacja: Obsłuż upuszczenie pliku na folder."""
        return self.main_window.file_operations_handler.handle_file_drop_on_folder(
            source_file_paths, target_folder_path
        )

    # === DIALOG OPERATIONS ===
    def show_preview_dialog(self, file_pair: FilePair):
        """Delegacja: Pokaż dialog podglądu."""
        return self.main_window.dialog_manager.show_preview_dialog(file_pair)

    def show_detailed_move_report(
        self, moved_pairs, detailed_errors, skipped_files, summary
    ):
        """Delegacja: Pokaż szczegółowy raport przenoszenia."""
        return self.main_window.dialog_manager.show_detailed_move_report(
            moved_pairs, detailed_errors, skipped_files, summary
        )

    def show_error_message(self, title: str, message: str):
        """Delegacja: Pokaż komunikat błędu."""
        return self.main_window.dialog_manager.show_error_message(title, message)

    def show_warning_message(self, title: str, message: str):
        """Delegacja: Pokaż komunikat ostrzeżenia."""
        return self.main_window.dialog_manager.show_warning_message(title, message)

    def show_info_message(self, title: str, message: str):
        """Delegacja: Pokaż komunikat informacyjny."""
        return self.main_window.dialog_manager.show_info_message(title, message)

    # === PROGRESS OPERATIONS ===
    def show_progress(self, percent: int, message: str):
        """Delegacja: Pokaż postęp."""
        return self.main_window.progress_manager.show_progress(percent, message)

    def hide_progress(self):
        """Delegacja: Ukryj postęp."""
        return self.main_window.progress_manager.hide_progress()

    def handle_worker_error(self, error_message: str):
        """Delegacja: Obsłuż błąd workera."""
        return self.main_window.progress_manager.handle_worker_error(error_message)

    # === THUMBNAIL OPERATIONS ===
    def update_thumbnail_size(self):
        """Delegacja: Zaktualizuj rozmiar miniaturek."""
        return self.main_window.thumbnail_size_manager.update_thumbnail_size()

    def on_resize_timer_timeout(self):
        """Delegacja: Obsłuż timeout timera resize."""
        return self.main_window.thumbnail_size_manager.on_resize_timer_timeout()

    # === CONTROLLER INTERFACE OPERATIONS ===
    def update_scan_results(self, scan_result):
        """Delegacja: Zaktualizuj wyniki skanowania."""
        return self.main_window.controller_interface_manager.update_scan_results(
            scan_result
        )

    def confirm_bulk_delete(self, count: int) -> bool:
        """Delegacja: Potwierdź masowe usuwanie."""
        return self.main_window.controller_interface_manager.confirm_bulk_delete(count)

    def update_after_bulk_operation(self, processed_pairs, operation_name: str):
        """Delegacja: Zaktualizuj po operacji masowej."""
        return (
            self.main_window.controller_interface_manager.update_after_bulk_operation(
                processed_pairs, operation_name
            )
        )

    def update_bulk_operations_visibility_controller(self, selected_count: int):
        """Delegacja: Zaktualizuj widoczność operacji masowych (kontroler)."""
        return self.main_window.controller_interface_manager.update_bulk_operations_visibility(
            selected_count
        )

    def add_new_pair(self, new_pair):
        """Delegacja: Dodaj nową parę."""
        return self.main_window.controller_interface_manager.add_new_pair(new_pair)

    def update_unpaired_lists(self, archives, previews):
        """Delegacja: Zaktualizuj listy niesparowanych."""
        return self.main_window.controller_interface_manager.update_unpaired_lists(
            archives, previews
        )

    def request_metadata_save(self):
        """Delegacja: Żądaj zapisu metadanych."""
        return self.main_window.controller_interface_manager.request_metadata_save()

    def set_working_directory(self, directory: str):
        """Delegacja: Ustaw katalog roboczy."""
        return self.main_window.controller_interface_manager.set_working_directory(
            directory
        )

    # === TABS OPERATIONS ===
    def on_explorer_folder_changed(self, path: str):
        """Delegacja: Obsłuż zmianę folderu eksploratora."""
        return self.main_window.tabs_manager.on_explorer_folder_changed(path)

    def on_explorer_file_selected(self, file_path: str):
        """Delegacja: Obsłuż selekcję pliku eksploratora."""
        return self.main_window.tabs_manager.on_explorer_file_selected(file_path)
